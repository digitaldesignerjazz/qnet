# QNET

Public protocol layer for **QNET / XCoin / QCoin** and **Wizard Q** runes.

Part of the Esslinger & Co. / Nexus ecosystem — mesh (NetBird / NovaNet / xMesh), incentives, agent swarms, prototypes. This repository is the **public** chain-and-rune surface.

**Status:** Wizard Q opcode spec v0.1 is **Proposed**. There is no live public QNET node in this repo. Casts default to dry-run.

## Wizard Q skill

Living caster for the rune office:

- [`skills/wizard-q/SKILL.md`](skills/wizard-q/SKILL.md) — skill (what to activate, how to cast, what is forbidden)
- [`skills/wizard-q/references/Wizard_Q_Rune_Opcodes_v0.1.md`](skills/wizard-q/references/Wizard_Q_Rune_Opcodes_v0.1.md) — opcode grimoire
- [`scripts/qnet_submit.py`](scripts/qnet_submit.py) — dual-sig submitter (NetBird + Kyber, ±300s freshness)
- [`examples/rune_peer_introduction.example.json`](examples/rune_peer_introduction.example.json) — skeleton for `0x02`

```bash
python3 scripts/qnet_submit.py examples/rune_peer_introduction.example.json --dry-run
```

Set `QNET_ROOT` if you want mempool/receipts somewhere other than `./.qnet`.

## Public rules

- No secrets, setup keys, Kyber private material, or mesh env files in this tree.
- No real-person names in rune `linked_entities` or public parameters. Hashes only.
- Utility incentives, not a securities pitch.

## Layout

| Path | What |
|------|------|
| `protocol/` | QNET protocol outline |
| `tokenomics/` | XCoin / Wizard Q outlines |
| `runes/` | additional rune notes |
| `integrations/` | mesh–chain–AI notes |
| `skills/wizard-q/` | **Wizard Q skill + opcode spec** |
| `scripts/` | public casters |
| `examples/` | placeholder runes |

License: MIT. Copyright 2026 Sven Normen Esslinger / digitaldesignerjazz / Esslinger & Co.
