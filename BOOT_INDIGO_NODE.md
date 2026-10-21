# Indigo-Lila Node — Boot-Vorbereitung

**Rune:** 0x53  
**Farbe:** Indigo `#4B0082` / Lila `#C77DFF`  
**Status:** pending_boot  
**Skript-Version:** v3.3 (konkreter Netbird-HTTP-Push)

## 1. Voraussetzungen auf dem Ziel-PC

```bash
# Netbird (empfohlen)
curl -fsSL https://pkgs.netbird.io/install.sh | sh
# Setup-Key vom Mesh-Admin holen und joinen:
netbird up --setup-key <SETUP_KEY>

# curl muss vorhanden sein für den Push
command -v curl || sudo apt install curl   # oder entsprechend
```

## 2. Skript installieren

```bash
sudo mkdir -p /opt/indigo-node
sudo cp scripts/indigo_node_boot.sh /opt/indigo-node/
sudo chmod +x /opt/indigo-node/indigo_node_boot.sh
```

## 3. Als Dienst starten (systemd)

```bash
sudo cp scripts/indigo-node.service /etc/systemd/system/
# Optional: Peer-IP setzen (in der Unit oder via override)
# sudo systemctl edit indigo-node.service
# [Service]
# Environment=NETBIRD_PEER_IP=100.x.y.z
# Environment=NETBIRD_PEER_PORT=8080
# Environment=NETBIRD_PEER_PATH=/pulse

sudo systemctl daemon-reload
sudo systemctl enable --now indigo-node.service
sudo systemctl status indigo-node.service
journalctl -u indigo-node.service -f
```

## 4. Manueller Testlauf (ohne Dienst)

```bash
# Mit Push (Peer-IP bekannt):
NETBIRD_PEER_IP=100.x.y.z ./scripts/indigo_node_boot.sh

# Nur lokal:
./scripts/indigo_node_boot.sh
```

## 5. Peer-IP-Integration (v3.3)

Wenn `NETBIRD_PEER_IP` gesetzt ist und Netbird verbunden ist, wird jedes Envelope per **HTTP POST** gesendet:

```
POST http://$NETBIRD_PEER_IP:$NETBIRD_PEER_PORT$NETBIRD_PEER_PATH
Content-Type: application/json
Body: last_mesh_envelope.json
```

- Default-Port: `8080`
- Default-Path: `/pulse`
- Timeout: 5 s
- Erfolg/Fehler wird geloggt (`Push OK` / `Push FAILED`)

## 6. Validierung

- `status/last_pulse.json` enthält Swatch-, Epochen- und Dynasty-Beat.
- Bei gesetzter Peer-IP: Journal zeigt `Push OK` oder `Push FAILED`.
- Topic: `nexus/mesh/v0`.

## Hinweise

- Hannover-Box ist abgeschaltet (Testlauf beendet). Diese Node ist der neue Indigo-Anker.
- Onyx ruht weiter. Memorial-Workflow im onyx-node-Repo bleibt aktiv.
- Referenz für Epochen-Beat: 2026-10-21 00:00 UTC → Startwert 740.276.000.
