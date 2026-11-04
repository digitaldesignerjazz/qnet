#!/usr/bin/env python3
"""qnetd - QNET node daemon (asyncio, stdlib only, binds 127.0.0.1 only).

One TCP port per node serves two protocols, detected from the first line:
  * HTTP/1.0  (GET /status, GET /runes, GET /ledger, POST /rune)
  * QNET peer protocol: newline-delimited JSON (hello, ping/pong, peers_req/peers, rune)

Runes use the Wizard Q envelope (scripts/qnet_envelope.py) and are applied to a
per-node ledger via scripts/qnet_logic.py (data-dir/ledger.json).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from qnet_envelope import is_valid, rune_hash  # noqa: E402
from qnet_logic import apply_rune, load_ledger, save_ledger  # noqa: E402

PROTO_VERSION = "qnet/0.1"
HOST = "127.0.0.1"
# Ports belonging to existing services on this box; never bind them.
RESERVED_PORTS = {7229, 8787, 36657, 37657, 38657, 40657, 47657}
LOOPBACK = {"127.0.0.1", "localhost"}
PING_INTERVAL = 3.0
PEER_TIMEOUT = 15.0
RECONNECT_MIN, RECONNECT_MAX = 1.0, 10.0
DEFAULT_TTL = 8
MAX_LINE = 1 << 20


def now() -> float:
    return time.time()


def iso(ts: float | None) -> str | None:
    return None if ts is None else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


class Peer:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, direction: str):
        self.reader, self.writer, self.direction = reader, writer, direction
        self.node_id: str | None = None
        self.listen_addr: str | None = None
        self.connected_at = now()
        self.last_seen = now()
        self.rtt_ms: float | None = None
        self.ping_sent: dict[str, float] = {}

    async def send(self, msg: dict[str, Any]) -> None:
        self.writer.write((json.dumps(msg, separators=(",", ":")) + "\n").encode())
        await self.writer.drain()

    def close(self) -> None:
        if not self.writer.is_closing():
            self.writer.close()


class Node:
    def __init__(self, node_id: str, port: int, peers: list[str], data_dir: Path,
                 freshness_s: int | None, allow_remote: bool):
        self.node_id, self.port = node_id, port
        self.seed_peers = peers
        self.data_dir = data_dir
        self.ledger_path = data_dir / "ledger.json"
        self.runes_dir = data_dir / "runes"
        self.freshness_s = freshness_s
        self.allow_remote = allow_remote
        self.started = now()
        self.peers: dict[str, Peer] = {}            # node_id -> live connection (hop 1)
        self.known: dict[str, dict[str, Any]] = {}  # learned via peer lists (hop >= 2)
        self.ledger = load_ledger(self.ledger_path)
        self.seen: dict[str, dict[str, Any]] = {a["hash"]: {"hops": a.get("hops"), "from": a.get("received_from")}
                                                for a in self.ledger["applied"]}
        self.stats = {"gossip_received": 0, "gossip_duplicates": 0, "gossip_forwarded": 0, "rejected": 0}
        self.server: asyncio.base_events.Server | None = None

    # ---------- logging ----------
    def log(self, msg: str) -> None:
        print(f"{iso(now())} [{self.node_id}] {msg}", flush=True)

    # ---------- server ----------
    async def start(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.runes_dir.mkdir(exist_ok=True)
        self.server = await asyncio.start_server(self.on_connect, HOST, self.port, limit=MAX_LINE)
        self.log(f"listening on {HOST}:{self.port} (peer protocol + HTTP), data={self.data_dir}")
        (self.data_dir / "qnetd.pid").write_text(f"{os.getpid()}\n")
        for addr in self.seed_peers:
            asyncio.create_task(self.dial_loop(addr))
        asyncio.create_task(self.maintenance())

    async def on_connect(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            first = await asyncio.wait_for(reader.readline(), timeout=10)
        except (asyncio.TimeoutError, ConnectionError, ValueError):
            writer.close(); return
        if first[:4] in (b"GET ", b"POST", b"HEAD"):
            await self.handle_http(first, reader, writer)
        else:
            peer = Peer(reader, writer, "inbound")
            await self.run_peer(peer, first)

    # ---------- outbound ----------
    async def dial_loop(self, addr: str) -> None:
        host, _, port_s = addr.rpartition(":")
        if host not in LOOPBACK and not self.allow_remote:
            self.log(f"refusing non-loopback peer {addr} (use --allow-remote-peers)"); return
        delay = RECONNECT_MIN
        while True:
            if any(p.listen_addr == f"{host}:{port_s}" or p.listen_addr == addr for p in self.peers.values()):
                await asyncio.sleep(RECONNECT_MAX); continue
            try:
                reader, writer = await asyncio.open_connection(host, int(port_s), limit=MAX_LINE)
                peer = Peer(reader, writer, "outbound")
                peer.listen_addr = addr
                await peer.send(self.hello())
                delay = RECONNECT_MIN
                await self.run_peer(peer, None)
            except (OSError, asyncio.TimeoutError) as e:
                self.log(f"dial {addr} failed: {e.__class__.__name__}; retry in {delay:.0f}s")
            await asyncio.sleep(delay)
            delay = min(delay * 2, RECONNECT_MAX)

    def hello(self) -> dict[str, Any]:
        return {"type": "hello", "node_id": self.node_id, "listen": f"{HOST}:{self.port}",
                "version": PROTO_VERSION, "ts": now()}

    # ---------- peer session ----------
    async def run_peer(self, peer: Peer, first: bytes | None) -> None:
        try:
            if first is not None:
                await self.on_message(peer, first)
            while not peer.reader.at_eof():
                line = await asyncio.wait_for(peer.reader.readline(), timeout=PEER_TIMEOUT)
                if not line:
                    break
                await self.on_message(peer, line)
        except (asyncio.TimeoutError, ConnectionError, ValueError) as e:
            self.log(f"peer {peer.node_id or '?'} dropped: {e.__class__.__name__}")
        finally:
            peer.close()
            if peer.node_id and self.peers.get(peer.node_id) is peer:
                del self.peers[peer.node_id]
                self.log(f"peer {peer.node_id} disconnected")

    async def on_message(self, peer: Peer, line: bytes) -> None:
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            raise ValueError("bad json")
        peer.last_seen = now()
        t = msg.get("type")
        if peer.node_id is None and t != "hello":
            raise ValueError("expected hello")
        if t == "hello":
            await self.on_hello(peer, msg)
        elif t == "ping":
            await peer.send({"type": "pong", "nonce": msg.get("nonce")})
        elif t == "pong":
            sent = peer.ping_sent.pop(str(msg.get("nonce")), None)
            if sent:
                peer.rtt_ms = round((now() - sent) * 1000, 2)
        elif t == "peers_req":
            await peer.send({"type": "peers", "peers": self.peer_list()})
        elif t == "peers":
            self.on_peers(peer, msg.get("peers", []))
        elif t == "rune":
            await self.on_gossip(peer, msg)

    async def on_hello(self, peer: Peer, msg: dict[str, Any]) -> None:
        nid = str(msg.get("node_id") or "")
        if not nid or nid == self.node_id:
            raise ValueError("self or empty node_id")
        if msg.get("version") != PROTO_VERSION:
            raise ValueError(f"version mismatch {msg.get('version')}")
        existing = self.peers.get(nid)
        if existing is not None and existing is not peer:
            raise ValueError(f"duplicate connection to {nid}")
        peer.node_id = nid
        peer.listen_addr = msg.get("listen") or peer.listen_addr
        self.peers[nid] = peer
        self.known.pop(nid, None)
        if peer.direction == "inbound":
            await peer.send(self.hello())
        self.log(f"handshake ok with {nid} ({peer.direction}, {peer.listen_addr})")
        await peer.send({"type": "peers_req"})

    def peer_list(self) -> list[dict[str, Any]]:
        out = [{"node_id": p.node_id, "addr": p.listen_addr, "hop": 1} for p in self.peers.values()]
        out += [{"node_id": k, "addr": v["addr"], "hop": v["hop"]} for k, v in self.known.items()]
        return out

    def on_peers(self, peer: Peer, entries: list[dict[str, Any]]) -> None:
        for e in entries:
            nid, hop = e.get("node_id"), e.get("hop")
            if not nid or nid == self.node_id or nid in self.peers or not isinstance(hop, int):
                continue
            cand = hop + 1
            cur = self.known.get(nid)
            if cur is None or cand < cur["hop"] or cur["via"] == peer.node_id:
                self.known[nid] = {"addr": e.get("addr"), "hop": cand, "via": peer.node_id, "learned_at": now()}

    # ---------- runes ----------
    async def on_gossip(self, peer: Peer, msg: dict[str, Any]) -> None:
        self.stats["gossip_received"] += 1
        rune, h = msg.get("rune"), msg.get("hash")
        if not isinstance(rune, dict) or rune_hash(rune) != h:
            self.stats["rejected"] += 1
            self.log(f"gossip from {peer.node_id}: hash mismatch, dropped"); return
        if h in self.seen:
            self.stats["gossip_duplicates"] += 1; return
        ttl, hops = int(msg.get("ttl", 0)), int(msg.get("hops", 0)) + 1
        res = self.accept(rune, h, hops=hops, received_from=peer.node_id, origin=msg.get("origin"))
        if res["ok"] and ttl > 1:
            await self.broadcast({**msg, "ttl": ttl - 1, "hops": hops}, exclude=peer.node_id)

    def accept(self, rune: dict[str, Any], h: str, hops: int, received_from: str | None,
               origin: str | None, freshness_s: int | None = None) -> dict[str, Any]:
        ok, errors = is_valid(rune, freshness_s=freshness_s)
        if not ok:
            self.stats["rejected"] += 1
            return {"ok": False, "status": 400, "errors": errors}
        try:
            entry = apply_rune(self.ledger, rune)
        except ValueError as e:
            self.stats["rejected"] += 1
            return {"ok": False, "status": 409, "errors": [str(e)]}
        entry.update({"hops": hops, "received_from": received_from, "origin": origin})
        save_ledger(self.ledger, self.ledger_path)
        (self.runes_dir / f"{h}.json").write_text(json.dumps(rune, indent=2) + "\n", encoding="utf-8")
        self.seen[h] = {"hops": hops, "from": received_from}
        self.log(f"applied {rune['opcode']} {rune['rune_id']} hash={h[:12]} hops={hops} "
                 f"from={received_from or 'local'}: {entry['effect']}")
        return {"ok": True, "status": 200, "hash": h, "entry": entry}

    async def broadcast(self, msg: dict[str, Any], exclude: str | None = None) -> int:
        n = 0
        for nid, p in list(self.peers.items()):
            if nid == exclude:
                continue
            try:
                await p.send(msg); n += 1
            except (ConnectionError, RuntimeError):
                pass
        self.stats["gossip_forwarded"] += n
        return n

    async def submit(self, rune: Any, ttl: int) -> dict[str, Any]:
        if not isinstance(rune, dict):
            return {"ok": False, "status": 400, "errors": ["rune must be a JSON object"]}
        h = rune_hash(rune)
        if h in self.seen:
            return {"ok": False, "status": 409, "errors": ["duplicate rune (already seen)"], "hash": h}
        res = self.accept(rune, h, hops=0, received_from=None, origin=self.node_id, freshness_s=self.freshness_s)
        if res["ok"]:
            res["forwarded_to"] = await self.broadcast(
                {"type": "rune", "rune": rune, "hash": h, "ttl": ttl, "hops": 0, "origin": self.node_id})
        return res

    # ---------- maintenance ----------
    async def maintenance(self) -> None:
        n = 0
        while True:
            await asyncio.sleep(PING_INTERVAL)
            n += 1
            for p in list(self.peers.values()):
                if now() - p.last_seen > PEER_TIMEOUT:
                    self.log(f"peer {p.node_id} timed out"); p.close(); continue
                nonce = f"{self.node_id}-{n}"
                p.ping_sent = {nonce: now()}
                try:
                    await p.send({"type": "ping", "nonce": nonce})
                    if n % 3 == 0:
                        await p.send({"type": "peers_req"})
                except (ConnectionError, RuntimeError):
                    p.close()
            for nid in [k for k, v in self.known.items() if now() - v["learned_at"] > PEER_TIMEOUT * 2]:
                del self.known[nid]

    # ---------- HTTP ----------
    def status(self) -> dict[str, Any]:
        peers = [{"node_id": p.node_id, "addr": p.listen_addr, "direction": p.direction, "hop": 1,
                  "connected_at": iso(p.connected_at), "last_seen": iso(p.last_seen),
                  "last_seen_ago_s": round(now() - p.last_seen, 2), "rtt_ms": p.rtt_ms}
                 for p in self.peers.values()]
        peers += [{"node_id": k, "addr": v["addr"], "hop": v["hop"], "via": v["via"],
                   "last_seen": iso(v["learned_at"]), "last_seen_ago_s": round(now() - v["learned_at"], 2)}
                  for k, v in self.known.items()]
        return {"node_id": self.node_id, "listen": f"{HOST}:{self.port}", "protocol": PROTO_VERSION,
                "pid": os.getpid(), "uptime_s": round(now() - self.started, 1),
                "mode": self.ledger.get("mode"), "live": self.ledger.get("live"),
                "peers": sorted(peers, key=lambda x: (x["hop"], x["node_id"])),
                "applied_runes": [{k: a.get(k) for k in ("rune_id", "opcode", "name", "hash", "hops",
                                                         "received_from", "origin", "applied_at", "effect")}
                                  for a in self.ledger["applied"]],
                "stats": self.stats, "ledger_path": str(self.ledger_path)}

    async def handle_http(self, first: bytes, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            method, target, _ = first.decode("latin-1").split(" ", 2)
            headers: dict[str, str] = {}
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=10)
                if line in (b"\r\n", b"\n", b""):
                    break
                k, _, v = line.decode("latin-1").partition(":")
                headers[k.strip().lower()] = v.strip()
            body = b""
            if int(headers.get("content-length", "0") or 0) > 0:
                body = await reader.readexactly(min(int(headers["content-length"]), MAX_LINE))
            url = urlparse(target)
            if method == "GET" and url.path in ("/", "/status"):
                code, payload = 200, self.status()
            elif method == "GET" and url.path == "/runes":
                code, payload = 200, {"applied": self.ledger["applied"]}
            elif method == "GET" and url.path == "/ledger":
                code, payload = 200, self.ledger
            elif method == "POST" and url.path == "/rune":
                ttl = int(parse_qs(url.query).get("ttl", [DEFAULT_TTL])[0])
                try:
                    rune = json.loads(body or b"null")
                except json.JSONDecodeError:
                    rune = None
                payload = await self.submit(rune, ttl)
                code = payload.pop("status")
            else:
                code, payload = 404, {"ok": False, "error": "not found"}
        except Exception as e:  # keep the node alive on malformed requests
            code, payload = 400, {"ok": False, "error": f"{e.__class__.__name__}: {e}"}
        data = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode()
        reason = {200: "OK", 400: "Bad Request", 404: "Not Found", 409: "Conflict"}.get(code, "OK")
        writer.write(f"HTTP/1.0 {code} {reason}\r\nContent-Type: application/json; charset=utf-8\r\n"
                     f"Content-Length: {len(data)}\r\nConnection: close\r\n\r\n".encode() + data)
        try:
            await writer.drain()
        finally:
            writer.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="QNET node daemon (127.0.0.1 only)")
    ap.add_argument("--node-id", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--peers", default="", help="host:port,host:port (loopback only by default)")
    ap.add_argument("--data-dir", type=Path, default=None, help="default: node/data/<node-id>")
    ap.add_argument("--freshness", type=int, default=300,
                    help="max rune age in seconds for local submits (0 = off); gossip is not age-checked")
    ap.add_argument("--allow-remote-peers", action="store_true", help="allow dialing non-loopback peers")
    a = ap.parse_args()
    if a.port in RESERVED_PORTS or not (1024 <= a.port <= 65535):
        print(f"port {a.port} is reserved or invalid", file=sys.stderr); return 2
    data_dir = a.data_dir or Path(__file__).resolve().parent / "data" / a.node_id
    peers = [p.strip() for p in a.peers.split(",") if p.strip()]
    node = Node(a.node_id, a.port, peers, data_dir, a.freshness or None, a.allow_remote_peers)

    async def run() -> None:
        await node.start()
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)
        await stop.wait()
        node.log("shutting down")
        node.server.close()
        for p in list(node.peers.values()):
            p.close()

    asyncio.run(run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
