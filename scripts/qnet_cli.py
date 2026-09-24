#!/usr/bin/env python3
"""Operator CLI for the proposed QNET local simulator."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qnet_envelope import NAME_TO_OPCODE, OPCODES, is_valid
from qnet_logic import LEDGER_PATH, apply_and_persist, load_ledger


def cmd_map(_: argparse.Namespace) -> int:
    rows = []
    for hex_id, spec in OPCODES.items():
        rows.append(
            {
                "opcode": hex_id,
                "name": spec["name"],
                "band": spec["band"],
                "high_value": spec["high_value"],
                "required": spec["required"],
            }
        )
    print(json.dumps(rows, indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    rune = json.loads(Path(args.rune_json).read_text(encoding="utf-8"))
    ok, errors = is_valid(rune, allow_draft=args.draft)
    print(json.dumps({"ok": ok, "errors": errors, "opcode": rune.get("opcode")}, indent=2))
    return 0 if ok else 2


def cmd_status(_: argparse.Namespace) -> int:
    ledger = load_ledger()
    summary = {
        "mode": ledger.get("mode"),
        "live": ledger.get("live"),
        "version": ledger.get("version"),
        "treasury_qcoin": ledger.get("treasury_qcoin"),
        "accounts": len(ledger.get("accounts", {})),
        "applied": len(ledger.get("applied", [])),
        "anchors": len(ledger.get("anchors", [])),
        "proposals": len(ledger.get("proposals", {})),
        "identities": len(ledger.get("identities", {})),
        "ledger_path": str(LEDGER_PATH),
        "updated_at": ledger.get("updated_at"),
    }
    print(json.dumps(summary, indent=2))
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    rune = json.loads(Path(args.rune_json).read_text(encoding="utf-8"))
    try:
        result = apply_and_persist(rune)
    except ValueError as e:
        print(json.dumps({"ok": False, "error": str(e)}, indent=2))
        return 5
    print(json.dumps({"ok": True, **result}, indent=2))
    return 0


def cmd_skeleton(args: argparse.Namespace) -> int:
    opcode = args.opcode
    if opcode in NAME_TO_OPCODE:
        name = opcode
        opcode = NAME_TO_OPCODE[name]
    spec = OPCODES.get(opcode)
    if not spec:
        print(json.dumps({"ok": False, "error": f"unknown opcode {args.opcode}"}, indent=2))
        return 2
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {key: "" for key in spec["required"]}
    for key in spec.get("optional", []):
        params[key] = None
    rune = {
        "opcode": opcode,
        "name": spec["name"],
        "version": "0.1",
        "rune_id": f"rune-{opcode[2:]}-{int(datetime.now(timezone.utc).timestamp())}",
        "timestamp": ts,
        "parameters": params,
        "signatures": {
            "netbird_signature": "",
            "kyber_signature": "" if spec["high_value"] else None,
        },
        "status": "draft",
    }
    text = json.dumps(rune, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="QNET proposed local CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("map", help="print assigned opcodes")
    p_val = sub.add_parser("validate", help="schema-check a rune JSON")
    p_val.add_argument("rune_json")
    p_val.add_argument("--draft", action="store_true")
    sub.add_parser("status", help="local ledger summary")
    p_app = sub.add_parser("apply", help="apply a valid rune to the local ledger")
    p_app.add_argument("rune_json")
    p_sk = sub.add_parser("skeleton", help="emit a draft envelope")
    p_sk.add_argument("opcode", help="0x50 or RUNE_NARRATIVE_ANCHOR")
    p_sk.add_argument("--out")
    args = parser.parse_args()
    return {
        "map": cmd_map,
        "validate": cmd_validate,
        "status": cmd_status,
        "apply": cmd_apply,
        "skeleton": cmd_skeleton,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
