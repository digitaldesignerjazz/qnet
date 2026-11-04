#!/usr/bin/env python3
"""QNet rune catch-up sync (stdlib only).

Fetches the source node's applied rune hashes (GET /runes), compares them with each
target's /status applied_runes, and POSTs missing envelopes unchanged to target /rune.
GET /runes returns ledger entries only (no envelopes), so original envelopes are taken
from --envelope files/dirs and used only if rune_hash(envelope) matches.
Pre-checks the target freshness window (qnetd default --freshness 300): stale runes would
be rejected by POST /rune, so they are reported and not sent.
"""
import argparse, json, sys, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from qnet_envelope import rune_hash, is_valid  # noqa: E402

def get(addr, path):
    with urllib.request.urlopen(f"http://{addr}{path}", timeout=10) as r:
        return json.load(r)

def post(addr, rune):
    req = urllib.request.Request(f"http://{addr}/rune", data=json.dumps(rune).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)

def load_envelopes(paths):
    env = {}
    for p in map(Path, paths):
        for f in (sorted(p.glob("*.json")) if p.is_dir() else [p]):
            try:
                r = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(r, dict):
                env[rune_hash(r)] = (r, str(f))
    return env

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--target", action="append", required=True)
    ap.add_argument("--envelope", action="append", default=[], help="envelope file or dir (hash-verified)")
    ap.add_argument("--freshness", type=int, default=300, help="target freshness window, 0=off")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = [e["hash"] for e in get(a.source, "/runes")["applied"]]
    envs = load_envelopes(a.envelope)
    rc = 0
    for t in a.target:
        have = {e["hash"] for e in get(t, "/status")["applied_runes"]}
        missing = [h for h in src if h not in have]
        print(f"[{t}] missing {len(missing)}: {[h[:8] for h in missing]}")
        for h in missing:
            if h not in envs:
                print(f"  {h[:8]}: no hash-verified envelope available -> skip"); rc = 1; continue
            rune, f = envs[h]
            ok, errs = is_valid(rune, freshness_s=a.freshness or None)
            if not ok:
                print(f"  {h[:8]} ({f}): would be rejected by POST /rune: {errs} -> skip"); rc = 1; continue
            if a.dry_run:
                print(f"  {h[:8]} ({f}): would POST"); continue
            code, res = post(t, rune)
            print(f"  {h[:8]}: HTTP {code} {res.get('hash', '')[:8]} {res.get('errors', '')}")
            rc |= code != 200
    return rc

if __name__ == "__main__":
    sys.exit(main())
