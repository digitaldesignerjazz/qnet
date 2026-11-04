#!/usr/bin/env python3
"""3-node mesh test: A <-> B <-> C on free localhost ports from 7301.

Submits a rune to A and checks that B (1 hop) and C (2 hops, via B) applied it,
that duplicates are rejected, invalid runes are refused, and that status shows
real peers. Stops only the processes it started (by their own PIDs).
Run: python3 node/tests/test_mesh.py
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

NODE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NODE_DIR))
from qnetctl import call, make_rune  # noqa: E402

RESERVED = {7229, 8787, 36657, 37657, 38657, 40657, 47657}


def free_ports(n: int, start: int = 7301) -> list[int]:
    ports, p = [], start
    while len(ports) < n and p < start + 500:
        if p not in RESERVED:
            with socket.socket() as s:
                try:
                    s.bind(("127.0.0.1", p)); ports.append(p)
                except OSError:
                    pass
        p += 1
    return ports


def wait_for(pred, timeout=20.0, step=0.25):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if pred():
                return True
        except (OSError, ValueError):
            pass
        time.sleep(step)
    return False


class MeshTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_dir = Path(f"/tmp/qnet-mesh-test-{time.strftime('%Y%m%d-%H%M%S')}")
        cls.run_dir.mkdir(parents=True)
        pa, pb, pc = cls.ports = free_ports(3)
        spec = [("node-a", pa, f"127.0.0.1:{pb}"), ("node-b", pb, ""), ("node-c", pc, f"127.0.0.1:{pb}")]
        cls.procs, cls.logs = {}, []
        for nid, port, peers in spec:
            log = open(cls.run_dir / f"{nid}.log", "w")
            cls.procs[nid] = subprocess.Popen(
                [sys.executable, str(NODE_DIR / "qnetd.py"), "--node-id", nid, "--port", str(port),
                 "--peers", peers, "--data-dir", str(cls.run_dir / nid)],
                stdout=log, stderr=subprocess.STDOUT)
            cls.logs.append(log)
        cls.port = dict(zip(["node-a", "node-b", "node-c"], cls.ports))
        print(f"\nstarted: " + ", ".join(f"{n} pid={p.pid} port={cls.port[n]}" for n, p in cls.procs.items()))

    @classmethod
    def tearDownClass(cls):
        for nid, p in cls.procs.items():
            p.terminate()
        for nid, p in cls.procs.items():
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill(); p.wait()
            print(f"stopped {nid} pid={p.pid} exit={p.returncode}")
        for log in cls.logs:
            log.close()
        print(f"logs/data: {cls.run_dir}")

    def status(self, nid):
        return call(self.port[nid], "GET", "/status")[1]

    def test_mesh(self):
        # 1) real handshakes: B sees A and C directly; A sees C at hop 2 via B
        def connected():
            b = {p["node_id"]: p for p in self.status("node-b")["peers"]}
            a = {p["node_id"]: p for p in self.status("node-a")["peers"]}
            return b.get("node-a", {}).get("hop") == 1 and b.get("node-c", {}).get("hop") == 1 \
                and a.get("node-c", {}).get("hop") == 2
        self.assertTrue(wait_for(connected), "mesh did not form")
        a = self.status("node-a")
        print("A peers:", json.dumps([{k: p.get(k) for k in ("node_id", "hop", "via", "last_seen_ago_s")}
                                      for p in a["peers"]]))

        # 2) ping/pong works (rtt measured)
        self.assertTrue(wait_for(lambda: self.status("node-a")["peers"][0].get("rtt_ms") is not None, 10))

        # 3) invalid rune is refused, nothing applied
        bad = make_rune(None); bad["signatures"]["netbird_signature"] = ""
        code, res = call(self.port["node-a"], "POST", "/rune", json.dumps(bad).encode())
        self.assertEqual(code, 400, res); print("invalid rune ->", code, res["errors"])

        # 4) submit to A; B and C must apply it
        rune = make_rune(None)
        code, res = call(self.port["node-a"], "POST", "/rune", json.dumps(rune).encode())
        self.assertEqual(code, 200, res)
        h = res["hash"]; print(f"submitted to A: hash={h[:16]} forwarded_to={res['forwarded_to']}")

        def applied(nid):
            return next((r for r in self.status(nid)["applied_runes"] if r["hash"] == h), None)
        self.assertTrue(wait_for(lambda: applied("node-b") and applied("node-c"), 10), "gossip failed")
        rb, rc = applied("node-b"), applied("node-c")
        print(f"B applied: hops={rb['hops']} from={rb['received_from']} | C applied: hops={rc['hops']} from={rc['received_from']}")
        self.assertEqual((rb["hops"], rb["received_from"]), (1, "node-a"))
        self.assertEqual((rc["hops"], rc["received_from"]), (2, "node-b"))

        # 5) per-node ledger file contains it
        for nid in self.procs:
            ledger = json.loads((self.run_dir / nid / "ledger.json").read_text())
            self.assertEqual([x["hash"] for x in ledger["applied"]], [h], nid)
            self.assertEqual(len(ledger["anchors"]), 1)

        # 6) dedup: resubmitting to A or C is refused, no double-apply anywhere
        self.assertEqual(call(self.port["node-a"], "POST", "/rune", json.dumps(rune).encode())[0], 409)
        self.assertEqual(call(self.port["node-c"], "POST", "/rune", json.dumps(rune).encode())[0], 409)
        time.sleep(1)
        for nid in self.procs:
            self.assertEqual(len(self.status(nid)["applied_runes"]), 1, nid)
        print("stats:", {n: self.status(n)["stats"] for n in self.procs})


if __name__ == "__main__":
    unittest.main(verbosity=2)
