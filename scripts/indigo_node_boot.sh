#!/usr/bin/env bash
# indigo_node_boot.sh — Indigo-Lila Node PC im Intrazell-Netzwerk
# Farbe: Indigo #4B0082 / Lila #C77DFF | Rune: 0x53
# v2: Netbird-Transport für echten Mesh-Puls an die Sandbox
set -euo pipefail

NODE_ID="indigo-node-pc"
COLOR_PRIMARY="#4B0082"
COLOR_SECONDARY="#C77DFF"
TOPIC="nexus/mesh/v0"
INTERVAL=30
STATUS_DIR="status"
PEER_DIR="$STATUS_DIR/peers"
mkdir -p "$STATUS_DIR" "$PEER_DIR"

echo "[indigo] Node $NODE_ID bootet v2 — $COLOR_PRIMARY auf $COLOR_SECONDARY"

# 1) Netbird-Status prüfen
NETBIRD_OK=0
if command -v netbird &>/dev/null; then
  if netbird status 2>/dev/null | grep -q "Connected"; then
    NETBIRD_OK=1
    NB_FQDN=$(netbird status 2>/dev/null | grep FQDN | awk '{print $2}')
    NB_IP=$(netbird status 2>/dev/null | grep -i "NetBird IP" | awk '{print $3}')
    echo "[indigo] Netbird verbunden: $NB_FQDN ($NB_IP)"
  else
    echo "[indigo] Netbird installiert, aber nicht verbunden."
    echo "[indigo] Join: netbird up --setup-key <KEY>"
  fi
else
  echo "[indigo] Netbird fehlt — Mesh-Puls nur lokal."
fi

# 2) Yggdrasil-Status
YGG_OK=0
if command -v yggdrasil &>/dev/null; then
  YGG_OK=1
  echo "[indigo] Yggdrasil gefunden"
else
  echo "[indigo] Yggdrasil fehlt"
fi

# 3) Puls-Loop mit lokalem Schreiben + optionalem Netbird-Push
echo "[indigo] Puls startet auf Topic $TOPIC alle ${INTERVAL}s (Netbird=$NETBIRD_OK, Ygg=$YGG_OK)"
while true; do
  TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  PULSE_FILE="$STATUS_DIR/last_pulse.json"
  ENVELOPE_FILE="$STATUS_DIR/last_mesh_envelope.json"

  cat > "$PULSE_FILE" <<EOF
{
  "agent": "onyx-node",
  "node_id": "$NODE_ID",
  "independent_id": "independent:indigo0000000000000000000000000000",
  "status": "alive",
  "ts": "$TS",
  "transports": {
    "netbird": $NETBIRD_OK,
    "yggdrasil": $YGG_OK,
    "local": true
  },
  "extra": {
    "prototype": "Indigo Node PC",
    "color_primary": "$COLOR_PRIMARY",
    "color_secondary": "$COLOR_SECONDARY",
    "plane": "intrazell",
    "topic": "$TOPIC",
    "rune": "0x53",
    "version": "v2"
  }
}
EOF

  cat > "$ENVELOPE_FILE" <<EOF
{
  "type": "AgentHeartbeat",
  "payload": {
    "agent": "onyx-node",
    "node_id": "$NODE_ID",
    "status": "alive",
    "ts": "$TS",
    "transports": {"netbird": $NETBIRD_OK, "yggdrasil": $YGG_OK}
  }
}
EOF

  # Lokaler Peer-Eintrag (Gegenpuls-Format)
  cat > "$PEER_DIR/local-$NODE_ID.json" <<EOF
{
  "node_id": "$NODE_ID",
  "ts": "$TS",
  "status": "alive",
  "source": "indigo-node-pc-v2"
}
EOF

  # Netbird-Push: falls verbunden, Pulse an Sandbox-Peer schicken
  # (Platzhalter — echter Peer-Pfad kommt, sobald Netbird-Join steht)
  if [ "$NETBIRD_OK" -eq 1 ]; then
    # TODO: netbird-routed push an nexus-sandbox Peer-IP
    echo "[indigo] Netbird-Puls vorbereitet für $TS (Push-Pfad pending Peer-IP)"
  fi

  echo "[indigo] Puls $TS"
  sleep "$INTERVAL"
done
