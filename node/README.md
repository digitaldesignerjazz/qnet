# qnetd – QNET-Node (Schritt 1)

Ein echter Node-Prozess: lauscht auf **einem Port nur auf 127.0.0.1**, verbindet sich mit Peers, tauscht Peer-Listen aus, verbreitet Runen per Gossip und wendet sie auf ein eigenes Ledger an. Nur Python-3-Standardbibliothek (asyncio). Status: **lokale Simulation** (`mode=local-sim`, `live=false`). Keine Chain-Anbindung, keine Token-Bewegungen.

## Dateien
- `qnetd.py`: Daemon
- `qnetctl.py`: CLI (`status`, `runes`, `submit`, `make-rune`)
- `tests/test_mesh.py`: 3-Node-Test
- `../scripts/qnet_envelope.py`: Opcode-Tabelle v0.1 + Validierung (wird auch von `qnet_cli.py` genutzt)
- `../scripts/qnet_logic.py`: Ledger + Anwenden von Runen (wird auch von `qnet_cli.py` genutzt)

## Start
```bash
cd /workspace/repos/qnet
python3 node/qnetd.py --node-id node-a --port 7301 --peers 127.0.0.1:7302 &
python3 node/qnetd.py --node-id node-b --port 7302 &
python3 node/qnetd.py --node-id node-c --port 7303 --peers 127.0.0.1:7302 &
python3 node/qnetctl.py --port 7301 status
python3 node/qnetctl.py make-rune --out /tmp/rune.json
python3 node/qnetctl.py --port 7301 submit /tmp/rune.json
python3 node/qnetctl.py --port 7303 runes        # Rune ist auf C angekommen (hops=2)
kill <pid>                                        # PID steht in data/<node-id>/qnetd.pid
```
Optionen: `--data-dir` (Standard: `node/data/<node-id>/`, git-ignoriert), `--freshness 300` (maximales Alter bei lokalem Einreichen, 0 = aus), `--allow-remote-peers` (standardmäßig nur Loopback-Peers).

## Ports
Vorschlag: 7301 und folgende. Gesperrt (der Node verweigert den Start): 7229, 8787, 36657, 37657, 38657, 40657, 47657. Gebunden wird immer nur `127.0.0.1`.

## Protokoll
Der Port erkennt das Protokoll an der ersten Zeile. Beginnt sie mit `GET`/`POST`, ist es HTTP, sonst Peer-Protokoll.

**HTTP:** `GET /status` (node-id, Peers mit hop/last_seen/rtt, angewendete Runen, Statistik), `GET /runes`, `GET /ledger`, `POST /rune[?ttl=8]` (Body = Runen-JSON; 200 angewendet, 400 ungültig, 409 Duplikat).

**Peer-Protokoll (TCP, eine JSON-Nachricht pro Zeile, Version `qnet/0.1`):**
| Nachricht | Inhalt |
|---|---|
| `hello` | `node_id`, `listen`, `version`. Der Dialer sendet zuerst, die Gegenseite antwortet. Verbindungen zu sich selbst und doppelte Verbindungen werden getrennt. |
| `ping` / `pong` | `nonce`, alle 3 s, ergibt `rtt_ms`. Ohne Nachricht für 15 s gilt der Peer als tot. Neuverbindung mit Backoff von 1 bis 10 s. |
| `peers_req` / `peers` | Liste `{node_id, addr, hop}`. Indirekte Peers erscheinen als `hop+1` mit `via`. |
| `rune` | `rune`, `hash`, `ttl`, `hops`, `origin`. Ablauf: Hash prüfen, Dedup über den Hash, validieren, anwenden, mit `ttl-1` an alle Peers außer dem Absender weitergeben. |

Hash = `sha256(json.dumps(rune, sort_keys=True))`, identisch mit `content_hash` aus `qnet_submit.py`.

## Runen-Format
Wizard-Q-Umschlag wie bei `qnet_cli.py skeleton` und `qnet_submit.py`: `opcode name version rune_id timestamp parameters signatures status`. Geprüft werden: bekannter Opcode, passender Name, Pflichtparameter (nicht leer, kein `TO_BE_FILLED`), Status `signed-ready|signed|ready`, `netbird_signature` vorhanden, bei High-Value-Opcodes zusätzlich `kyber_signature`.
**Wichtig:** Signaturen werden nur auf **Vorhandensein** geprüft, nicht kryptografisch. Die Freie-Form-Dateien in `runes/` (z. B. `RUNE_INDIGO_LILA_NODE_0x52.json`) haben kein Umschlagformat und werden abgelehnt.

## Test
```bash
python3 node/tests/test_mesh.py
```
Der Test startet A–B–C auf freien Ports ab 7301, reicht eine Rune bei A ein und prüft, dass B sie mit hop 1 und C mit hop 2 angewendet hat. Er prüft außerdem Dedup, die Ablehnung ungültiger Runen und die Ledger-Dateien. Danach beendet er nur die eigenen PIDs. Logs und Daten liegen in `/tmp/qnet-mesh-test-*`.
