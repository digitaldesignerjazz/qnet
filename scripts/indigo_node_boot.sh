#!/usr/bin/env bash
# indigo_node_boot.sh — Indigo-Lila Node PC im Intrazell-Netzwerk
# Farbe: Indigo #4B0082 / Lila #C77DFF | Rune: 0x53
# v3.3: konkreter Netbird HTTP-Push (curl POST) über Peer-IP
set -euo pipefail

NODE_ID="${NODE_ID:-indigo-node-pc}"
COLOR_PRIMARY="#4B0082"
COLOR_SECONDARY="#C77DFF"
TOPIC="nexus/mesh/v0"
INTERVAL=30
STATUS_DIR="${STATUS_DIR:-status}"
PEER_DIR="$STATUS_DIR/peers"
mkdir -p "$STATUS_DIR" "$PEER_DIR"

# Peer-Integration (Netbird)
NETBIRD_PEER_IP="${NETBIRD_PEER_IP:-}"
NETBIRD_PEER_PORT="${NETBIRD_PEER_PORT:-8080}"
NETBIRD_PEER_PATH="${NETBIRD_PEER_PATH:-/pulse}"

# Swatch-Beat: Biel Mean Time, 1 Beat = 86.4s
swatch_beat() {
  local now_utc epoch_bmt
  now_utc=$(date -u +%s)
  epoch_bmt=$((now_utc + 3600))
  local sod=86400
  local beat=864
  echo $(( (epoch_bmt % sod) * 1000 / beat ))
}

# Epochen-Beat seit Christi Geburt (Referenz 2026-10-21 00:00 UTC)
epochen_beat() {
  local now_utc days
  now_utc=$(date -u +%s)
  days=$(( (now_utc - 1792540800) / 86400 ))
  echo $((740276000 + days * 1000))
}

# Dynasty-Beat seit 23.10.1998
dynasty_beat() {
  local now_utc days
  now_utc=$(date -u +%s)
  days=$(( (now_utc - 909273600) / 86400 ))
  echo $((10225000 + days * 1000))
}

echo "[indigo] Node $NODE_ID bootet v3.3 — $COLOR_PRIMARY auf $COLOR_SECONDARY"

# Netbird-Status
NETBIRD_OK=0
if command -v netbird &>/dev/null; then
  if netbird status 2>/dev/null | grep -q "Connected"; then
    NETBIRD_OK=1
    NB_FQDN=$(netbird status 2>/dev/null | grep FQDN | awk '{print $2}' || true)
    NB_IP=$(netbird status 2>/dev/null | grep -i "NetBird IP" | awk '{print $3}' || true)
    echo "[indigo] Netbird verbunden: ${NB_FQDN:-unknown} (${NB_IP:-unknown})"
  else
    echo "[indigo] Netbird installiert, aber nicht verbunden. Join mit: netbird up --setup-key <KEY>"
  fi
else
  echo "[indigo] Netbird fehlt — Mesh-Puls nur lokal."
fi

# Yggdrasil
YGG_OK=0
if command -v yggdrasil &>/dev/null; then
  YGG_OK=1
  echo "[indigo] Yggdrasil gefunden"
else
  echo "[indigo] Yggdrasil fehlt"
fi

echo "[indigo] Puls startet auf Topic $TOPIC alle ${INTERVAL}s (Netbird=$NETBIRD_OK, Ygg=$YGG_OK)"
if [ -n "$NETBIRD_PEER_IP" ]; then
  echo "[indigo] Netbird-Push aktiv → http://${NETBIRD_PEER_IP}:${NETBIRD_PEER_PORT}${NETBIRD_PEER_PATH}"
fi

while true; do
  TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  SB=$(swatch_beat)
  EB=$(epochen_beat)
  DB=$(dynasty_beat)
  PULSE_FILE="$STATUS_DIR/last_pulse.json"
  ENVELOPE_FILE="$STATUS_DIR/last_mesh_envelope.json"

  cat > "$PULSE_FILE" <<EOF
{
  "agent": "onyx-node",
  "node_id": "$NODE_ID",
  "independent_id": "independent:indigo0000000000000000000000000000",
  "status": "alive",
  "ts": "$TS",
  "swatch_beat": "@$SB",
  "epochen_beat": $EB,
  "dynasty_beat": $DB,
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
    "version": "v3.3"
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
    "swatch_beat": "@$SB",
    "epochen_beat": $EB,
    "dynasty_beat": $DB,
    "transports": {"netbird": $NETBIRD_OK, "yggdrasil": $YGG_OK}
  }
}
EOF

  # Konkreter Netbird-Push via HTTP POST
  if [ -n "$NETBIRD_PEER_IP" ] && [ "$NETBIRD_OK" -eq 1 ]; then
    PUSH_URL="http://${NETBIRD_PEER_IP}:${NETBIRD_PEER_PORT}${NETBIRD_PEER_PATH}"
    if command -v curl &>/dev/null; then
      if curl -sS -m 5 -X POST -H "Content-Type: application/json" \
           --data @"$ENVELOPE_FILE" "$PUSH_URL" >/dev/null 2>&1; then
        echo "[indigo] Push OK → $PUSH_URL"
      else
        echo "[indigo] Push FAILED → $PUSH_URL"
      fi
    else
      echo "[indigo] curl fehlt — Push nicht möglich"
    fi
  fi

  echo "[indigo] Puls $TS — Swatch @$SB, Epochen $EB, Dynasty $DB"
  sleep "$INTERVAL"
done
