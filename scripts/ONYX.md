# QNET simulator on Onyx

Proposed v0.1. Not a live chain.

```bash
export NEXUS_ROOT="$HOME/artifacts/nexus"
mkdir -p "$NEXUS_ROOT/qnet/drafts" "$NEXUS_ROOT/mempool" "$NEXUS_ROOT/receipts" "$HOME/src"
cd "$HOME/src"
git clone https://github.com/digitaldesignerjazz/qnet.git
cd "$HOME/src/qnet/scripts"
python3 qnet_cli.py status
python3 qnet_cli.py skeleton 0x01 --out "$NEXUS_ROOT/qnet/drafts/HEARTBEAT.json"
```

Fill the draft (`signed-ready`, overlay placeholder signature, local mesh fingerprint). Then:

```bash
python3 qnet_submit.py "$NEXUS_ROOT/qnet/drafts/HEARTBEAT.json" --dry-run
```

Do not copy live `independent:<hex>` values back into public commits.
