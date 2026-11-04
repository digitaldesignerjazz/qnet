#!/usr/bin/env python3
"""qnetctl - talk to a local qnetd over its HTTP endpoint (127.0.0.1 only).

  qnetctl.py --port 7301 status
  qnetctl.py --port 7301 runes
  qnetctl.py --port 7301 submit rune.json [--ttl 8]
  qnetctl.py make-rune --content-hash <sha256> [--out rune.json]   # fresh 0x50 test rune
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def call(port: int, method: str, path: str, body: bytes | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def make_rune(content_hash: str | None, anchor_type: str = "agent_story") -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ch = content_hash or hashlib.sha256(f"qnet-test-{time.time_ns()}".encode()).hexdigest()
    return {
        "opcode": "0x50", "name": "RUNE_NARRATIVE_ANCHOR", "version": "0.1",
        "rune_id": f"rune-50-{time.time_ns()}", "timestamp": ts,
        "parameters": {"anchor_type": anchor_type, "content_hash": ch, "linked_entities": ["qnet-local-test"]},
        # Placeholder: presence-checked only, no cryptographic verification yet.
        "signatures": {"netbird_signature": "local-test-unsigned", "kyber_signature": None},
        "status": "signed-ready",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="qnetd client")
    ap.add_argument("--port", type=int, default=7301)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status"); sub.add_parser("runes")
    s = sub.add_parser("submit"); s.add_argument("rune_json"); s.add_argument("--ttl", type=int, default=8)
    m = sub.add_parser("make-rune"); m.add_argument("--content-hash"); m.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "make-rune":
        text = json.dumps(make_rune(a.content_hash), indent=2) + "\n"
        if a.out:
            Path(a.out).write_text(text, encoding="utf-8")
        print(text, end=""); return 0
    if a.cmd == "submit":
        code, res = call(a.port, "POST", f"/rune?ttl={a.ttl}", Path(a.rune_json).read_bytes())
    else:
        code, res = call(a.port, "GET", "/" + a.cmd)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if code == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
