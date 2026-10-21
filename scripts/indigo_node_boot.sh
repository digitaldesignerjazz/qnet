#!/usr/bin/env bash
# indigo_node_boot.sh — Indigo-Lila Node PC im Intrazell-Netzwerk
# Farbe: Indigo #4B0082 / Lila #C77DFF | Rune: 0x53
set -euo pipefail

NODE_ID="indigo-node-pc"
COLOR_PRIMARY="#4B0082"
COLOR_SECONDARY="#C77DFF"
TOPIC="nexus/mesh/v0"
INTERVAL=30
STATUS_DIR="status"
mkdir -p "$STATUS_DIR"

echo "[indigo] Node $NODE_ID bootet — $COLOR_PRIMARY auf $COLOR_SECONDARY"

# 1) Netbird joinen (falls installiert und nicht verbunden)
if command -v netbird &>/dev/null; then
  if ! netbird status 2>/dev/null | grep -q "Connected"; then
    echo "[indigo] Netbird nicht verbunden — bitte Setup-Key setzen: netbird up --setup-key <KEY>"
  else
    echo "[indigo] Netbird verbunden: $(netbird status 2>/dev/null | grep FQDN | awk '{print $2}')"
  fi
else
  echo "[indigo] Netbird fehlt — optional installieren"
fi

# 2) Yggdrasil (falls vorhanden)
if command -v yggdrasil &>/dev/null; then
  echo "[indigo] Yggdrasil gefunden"
else
  echo "[indigo] Yggdrasil fehlt — Mesh läuft über Netbird/QNET"
fi

# 3) Puls-Loop
echo "[indigo] Puls startet auf Topic $TOPIC alle ${INTERVAL}s"
while true; do
  TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  cat > "$STATUS_DIR/last_pulse.json" <<EOF
{
  "agent": "onyx-node",
  "node_id": "$NODE_ID",
  "independent_id": "independent:indigo0000000000000000000000000000",
  "status": "alive",
  "ts": "$TS",
  "extra": {
    "prototype": "Indigo Node PC",
    "color_primary": "$COLOR_PRIMARY",
    "color_secondary": "$COLOR_SECONDARY",
    "plane": "intrazell",
    "topic": "$TOPIC",
    "rune": "0x53"
  }
}
EOF
  cat > "$STATUS_DIR/last_mesh_envelope.json" <<EOF
{
  "type": "AgentHeartbeat",
  "payload": {
    "agent": "onyx-node",
    "node_id": "$NODE_ID",
    "status": "alive",
    "ts": "$TS"
  }
}
EOF
  echo "[indigo] Puls $TS"
  sleep "$INTERVAL"
done
