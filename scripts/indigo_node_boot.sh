#!/usr/bin/env bash
# indigo_node_boot.sh — Indigo-Lila Node PC im Intrazell-Netzwerk
# Farbe: Indigo #4B0082 / Lila #C77DFF | Rune: 0x53
# v3: Swatch-Zeit + Epochen-Beat + Dynasty-Beat im Puls-Envelope
set -euo pipefail

NODE_ID="indigo-node-pc"
COLOR_PRIMARY="#4B0082"
COLOR_SECONDARY="#C77DFF"
TOPIC="nexus/mesh/v0"
INTERVAL=30
STATUS_DIR="status"
PEER_DIR="$STATUS_DIR/peers"
mkdir -p "$STATUS_DIR" "$PEER_DIR"

# Swatch-Beat: Biel Mean Time, 1 Beat = 86.4s, Tag startet @000 um 00:00 BMT
swatch_beat() {
  local now_utc epoch_bmt
  now_utc=$(date -u +%s)
  epoch_bmt=$((now_utc + 3600))  # UTC+1 = Biel Mean Time
  local sod=86400
  local beat=864
  echo $(( (epoch_bmt % sod) * 1000 / beat ))
}

# Epochen-Beat seit Christi Geburt: 740.276.000 + Tage seit 2026-10-21 * 1000
epochen_beat() {
  local now_utc days
  now_utc=$(date -u +%s)
  days=$(( (now_utc - 1708387200) / 86400 ))  # 2024-02-20 00:00 UTC als Referenz
  echo $((740276000 + days * 1000))
}

# Dynasty-Beat seit 23.10.1998: 10.225.000 + Tage * 1000
dynasty_beat() {
  local now_utc days
  now_utc=$(date -u +%s)
  days=$(( (now_utc - 909273600) / 86400 ))  # 1998-10-23 00:00 UTC
  echo $((10225000 + days * 1000))
}

echo "[indigo] Node $NODE_ID bootet v3 — $COLOR_PRIMARY auf $COLOR_SECONDARY"

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

# 3) Puls-Loop mit Swatch/Epochen/Dynasty im Envelope
echo "[indigo] Puls startet auf Topic $TOPIC alle ${INTERVAL}s (Netbird=$NETBIRD_OK, Ygg=$YGG_OK)"
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
    "version": "v3"
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

  cat > "$PEER_DIR/local-$NODE_ID.json" <<EOF
{
  "node_id": "$NODE_ID",
  "ts": "$TS",
  "swatch_beat": "@$SB",
  "epochen_beat": $EB,
  "dynasty_beat": $DB,
  "status": "alive",
  "source": "indigo-node-pc-v3"
}
EOF

  if [ "$NETBIRD_OK" -eq 1 ]; then
    echo "[indigo] Netbird-Puls vorbereitet für $TS (Push-Pfad pending Peer-IP)"
  fi

  echo "[indigo] Puls $TS — Swatch @$SB, Epochen $EB, Dynasty $DB"
  sleep "$INTERVAL"
done
