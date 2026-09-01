#!/usr/bin/env python3
"""
qnet_submit.py — Lift signed Rune offerings into the QNET air
Nexus Ecosystem | Wizard Q Runes → local mempool / future chain

Usage:
  python3 qnet_submit.py <signed_rune.json> [--dry-run] [--endpoint URL]

Performs:
  - structural check
  - dual-signature gate (NetBird + Kyber present)
  - freshness window (±5 min default)
  - issues receipt + rune_id
  - writes to local mempool and (future) broadcasts to QNET node
"""

import argparse
import json
import hashlib
import os
import sys
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

NEXUS_ROOT = Path(os.environ.get("QNET_ROOT", os.environ.get("NEXUS_ROOT", "./.qnet")))
MEMPOOL_DIR = NEXUS_ROOT / "mempool"
RECEIPTS_DIR = NEXUS_ROOT / "receipts"
MEMPOOL_DIR.mkdir(parents=True, exist_ok=True)
RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

FRESHNESS_WINDOW_SECONDS = 300  # 5 minutes


def log(msg: str) -> None:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}")


def load_rune(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def structural_check(rune: Dict[str, Any]) -> bool:
    required = ["opcode", "name", "version", "rune_id", "timestamp", "parameters", "signatures", "status"]
    for k in required:
        if k not in rune:
            log(f"STRUCTURAL FAIL: missing key '{k}'")
            return False
    if rune["opcode"] != "0x02" and rune.get("name") != "RUNE_PEER_INTRODUCTION":
        log(f"Note: opcode {rune['opcode']} — proceeding (peer-intro optimized)")
    params = rune["parameters"]
    for p in ["introducer_fingerprint", "new_peer_fingerprint", "connection_proof", "timestamp"]:
        if p not in params or not params[p] or str(params[p]).startswith("TO_BE_FILLED"):
            log(f"STRUCTURAL FAIL: parameters.{p} incomplete")
            return False
    if rune["status"] not in ("signed-ready", "signed", "ready"):
        log(f"STRUCTURAL FAIL: status='{rune['status']}' — must be signed-ready / signed / ready")
        return False
    log("Structural check: PASS")
    return True


def dual_signature_gate(rune: Dict[str, Any]) -> bool:
    sigs = rune.get("signatures", {})
    nb = sigs.get("netbird_signature") or sigs.get("yggdrasil_signature")
    kyber = sigs.get("kyber_signature")
    if not nb or nb is None or str(nb).lower() in ("null", "none", ""):
        log("DUAL-SIG GATE FAIL: netbird_signature missing")
        return False
    if not kyber or kyber is None or str(kyber).lower() in ("null", "none", ""):
        log("DUAL-SIG GATE FAIL: kyber_signature missing (PQC required for high-value runes)")
        return False
    log(f"Dual-signature gate: PASS (netbird={str(nb)[:16]}… kyber={str(kyber)[:16]}…)")
    return True


def freshness_window(rune: Dict[str, Any], window: int = FRESHNESS_WINDOW_SECONDS) -> bool:
    try:
        ts_str = rune["timestamp"]
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        ts = datetime.datetime.fromisoformat(ts_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = abs((now - ts).total_seconds())
        if delta > window:
            log(f"FRESHNESS FAIL: age {delta:.0f}s > window {window}s")
            return False
        log(f"Freshness window: PASS (age {delta:.1f}s)")
        return True
    except Exception as e:
        log(f"FRESHNESS FAIL: cannot parse timestamp — {e}")
        return False


def issue_receipt(rune: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    rune_id = rune["rune_id"]
    content_hash = hashlib.sha256(json.dumps(rune, sort_keys=True).encode()).hexdigest()
    receipt = {
        "receipt_id": f"rcpt-{rune_id}",
        "rune_id": rune_id,
        "content_hash": content_hash,
        "accepted_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "accepted_local_mempool",
        "qnet_endpoint": "local" if dry_run else "pending_broadcast",
        "rewards": {
            "introducer_qcoin_hint": "small base + reputation",
            "crystallization": "pending settlement"
        },
        "notes": "Local mempool acceptance. Future QNET node will gossip + settle to ledger."
    }
    receipt_path = RECEIPTS_DIR / f"{receipt['receipt_id']}.json"
    if not dry_run:
        with open(receipt_path, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)
        mempool_path = MEMPOOL_DIR / f"{rune_id}.json"
        with open(mempool_path, "w", encoding="utf-8") as f:
            json.dump(rune, f, indent=2)
        log(f"Receipt written: {receipt_path}")
        log(f"Rune in local mempool: {mempool_path}")
    else:
        log("DRY-RUN: receipt would be issued, no files written")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="QNET Rune Submitter — dual-sig gate + mempool")
    parser.add_argument("rune_json", type=Path, help="Path to signed Rune JSON")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, no write")
    parser.add_argument("--endpoint", default="local", help="Future QNET endpoint URL")
    parser.add_argument("--window", type=int, default=FRESHNESS_WINDOW_SECONDS, help="Freshness seconds")
    args = parser.parse_args()

    log("=== qnet_submit.py — lifting signed offering into the air ===")

    if not args.rune_json.exists():
        log(f"ERROR: file not found {args.rune_json}")
        return 1

    try:
        rune = load_rune(args.rune_json)
    except Exception as e:
        log(f"ERROR loading JSON: {e}")
        return 1

    log(f"Loaded rune_id={rune.get('rune_id')} opcode={rune.get('opcode')}")

    if not structural_check(rune):
        log("REJECTED: structural")
        return 2
    if not dual_signature_gate(rune):
        log("REJECTED: dual-signature gate")
        return 3
    if not freshness_window(rune, args.window):
        log("REJECTED: freshness window")
        return 4

    receipt = issue_receipt(rune, dry_run=args.dry_run)
    log("=== ACCEPTED ===")
    log(f"Receipt ID: {receipt['receipt_id']}")
    log(f"Content hash: {receipt['content_hash'][:32]}…")
    log("Rune settles into local mempool / future chain. Rewards begin to crystallize.")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
