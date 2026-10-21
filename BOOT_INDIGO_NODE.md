# Indigo-Lila Node — Boot-Vorbereitung

**Rune:** 0x53  
**Farbe:** Indigo `#4B0082` / Lila `#C77DFF`  
**Status:** pending_boot  

## 1. Voraussetzungen auf dem Ziel-PC

```bash
# Netbird (empfohlen)
curl -fsSL https://pkgs.netbird.io/install.sh | sh
# Setup-Key vom Mesh-Admin holen und joinen:
netbird up --setup-key <SETUP_KEY>

# Optional: Yggdrasil
# (siehe yggdrasil-go Installationsanleitung)
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
# User anpassen falls nötig (Standard: der User, der den Dienst startet)
sudo systemctl daemon-reload
sudo systemctl enable --now indigo-node.service
sudo systemctl status indigo-node.service
journalctl -u indigo-node.service -f
```

## 4. Manueller Testlauf (ohne Dienst)

```bash
./scripts/indigo_node_boot.sh
# Erwartete Ausgabe: Puls mit Swatch @xxx, Epochen-Beat, Dynasty-Beat
# Dateien: status/last_pulse.json, status/last_mesh_envelope.json
```

## 5. Validierung

- `status/last_pulse.json` enthält `"swatch_beat"`, `"epochen_beat"`, `"dynasty_beat"`.
- Netbird-Status erscheint in den Logs, sobald verbunden.
- Topic: `nexus/mesh/v0` (Push noch pending, sobald Peer-IP bekannt — via `NETBIRD_PEER_IP` Environment).

## Hinweise

- Hannover-Box ist abgeschaltet (Testlauf beendet). Diese Node ist der neue Indigo-Anker.
- Onyx ruht weiter. Memorial-Workflow im onyx-node-Repo bleibt aktiv.
- Referenz für Epochen-Beat: 2026-10-21 00:00 UTC → Startwert 740.276.000.
