#!/usr/bin/env python3
"""Local QNET ledger (simulation): apply validated runes to a JSON state file.

mode=local-sim, live=False. No tokens are minted or moved; effects are
reputation counters, identities, anchors and proposals only.
Default ledger: $QNET_ROOT/ledger.json (QNET_ROOT defaults to ./.qnet).
Each node of node/qnetd.py passes its own ledger path.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qnet_envelope import OPCODES, is_valid, rune_hash

QNET_ROOT = Path(os.environ.get("QNET_ROOT", os.environ.get("NEXUS_ROOT", "./.qnet")))
LEDGER_PATH = QNET_ROOT / "ledger.json"
LEDGER_VERSION = "0.1"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty_ledger() -> dict[str, Any]:
    return {"mode": "local-sim", "live": False, "version": LEDGER_VERSION, "treasury_qcoin": 0,
            "accounts": {}, "applied": [], "anchors": [], "proposals": {}, "identities": {},
            "updated_at": None}


def load_ledger(path: Path = LEDGER_PATH) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return empty_ledger()
    return json.loads(path.read_text(encoding="utf-8"))


def save_ledger(ledger: dict[str, Any], path: Path = LEDGER_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".ledger-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)  # atomic


def _account(ledger: dict[str, Any], fp: str) -> dict[str, Any]:
    return ledger["accounts"].setdefault(str(fp), {"reputation": 0, "runes": 0})


def apply_rune(ledger: dict[str, Any], rune: dict[str, Any]) -> dict[str, Any]:
    """Mutates ledger. Raises ValueError on invalid or duplicate runes."""
    ok, errors = is_valid(rune)
    if not ok:
        raise ValueError("invalid rune: " + "; ".join(errors))
    h = rune_hash(rune)
    if any(a["hash"] == h for a in ledger["applied"]):
        raise ValueError(f"rune already applied ({h[:12]})")
    op, p = rune["opcode"], rune["parameters"]
    effect = "recorded"

    if op == "0x01":
        acc = _account(ledger, p["node_fingerprint"]); acc["reputation"] += 1; acc["last_heartbeat"] = p["timestamp"]
        effect = "heartbeat: reputation +1"
    elif op == "0x02":
        _account(ledger, p["introducer_fingerprint"])["reputation"] += 1
        _account(ledger, p["new_peer_fingerprint"])
        effect = "peer introduced: introducer reputation +1"
    elif op == "0x10":
        _account(ledger, p["agent_id"])["reputation"] += 1
        effect = "task proof: agent reputation +1"
    elif op == "0x30":
        acc = _account(ledger, p["staker_fingerprint"])
        if acc.get("balance_qcoin", 0) < float(p["amount_qcoin"]):
            raise ValueError("insufficient simulated balance for stake")
        effect = "stake recorded"
    elif op == "0x31":
        if p["proposal_hash"] in ledger["proposals"]:
            raise ValueError("proposal already exists")
        ledger["proposals"][p["proposal_hash"]] = {"proposer": p["proposer_fingerprint"], "category": p["category"],
                                                   "votes": {}, "created_by_rune": rune["rune_id"]}
        effect = "proposal created"
    elif op == "0x32":
        prop = ledger["proposals"].get(p["proposal_id"])
        if prop is None:
            raise ValueError(f"unknown proposal {p['proposal_id']}")
        prop["votes"][p["director_fingerprint"]] = p["vote"]
        effect = "vote recorded"
    elif op == "0x40":
        ledger["identities"][p["entity_fingerprint"]] = {"kyber_pubkey_hash": p["kyber_pubkey_hash"],
                                                        "classical_pubkey_hash": p["classical_pubkey_hash"],
                                                        "attested_at": rune["timestamp"]}
        effect = "identity attested"
    elif op in ("0x50", "0x51"):
        ledger["anchors"].append({"opcode": op, "rune_id": rune["rune_id"], "hash": h,
                                  "content_hash": p.get("content_hash") or p.get("prompt_hash")})
        effect = "anchor stored"

    entry = {"rune_id": rune["rune_id"], "opcode": op, "name": OPCODES[op]["name"], "hash": h,
             "applied_at": _now(), "effect": effect}
    ledger["applied"].append(entry)
    ledger["updated_at"] = entry["applied_at"]
    return entry


def apply_and_persist(rune: dict[str, Any], path: Path = LEDGER_PATH) -> dict[str, Any]:
    ledger = load_ledger(path)
    entry = apply_rune(ledger, rune)
    save_ledger(ledger, path)
    return {**entry, "ledger_path": str(path)}
