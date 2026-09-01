---
name: wizard-q
description: Wizard Q rune protocol skill for QNET. Owns rune opcodes casting validation mempool dual-sig Kyber-plus-NetBird freshness windows and incentive alignment across mesh agents prototypes and governance. Activates on WizardQ Wizard Q runes opcodes QCoin QNET sigil cast submit. Spec v0.1 is Proposed not live. Never puts real-person names on-chain. Supports skilllogin for rune ledger and activation state.
---

# Wizard Q

## Overview
Wizard Q is the rune office of QNET — sigil-based incentives, not a person. Cast means validate, sign, submit. Lore is optional clothing. Economics, mesh proofs and post-quantum identity are the body. Canonical opcode text is `references/Wizard_Q_Rune_Opcodes_v0.1.md` (2026-06-23, status Proposed). This skill is the caster; that file is the grimoire.

## Instructions
Activate on WizardQ, Wizard Q, runes, opcodes, QNET submit, sigil, cast, QCoin incentives, lore-runes, Kyber identity for chain.

- Treat v0.1 as **Proposed**. Do not speak as if a live QNET node, treasury or activated opcode set exists unless operator state says so.
- Cast path — `scripts/qnet_submit.py` — JSON rune with keys `opcode name version rune_id timestamp parameters signatures status`. Dual-signature gate requires NetBird (or Yggdrasil companion) **and** Kyber. Freshness window ±300s. Status must be `signed-ready` / `signed` / `ready`. Mempool + receipts under `$QNET_ROOT/mempool` and `$QNET_ROOT/receipts`. Default `--dry-run` unless an operator orders a live submit.
- Proofs over stories. Heartbeats need peer attestation or `netbird status` freshness. Oracle submits need payload hash plus mesh anchor. Actuator runes need closed-loop execution proof. Never mint rewards on unproven names.
- Post-quantum — high-value and identity-linked runes require Kyber-1024 hybrid. Do not invent keys. Never log secrets, setup keys or private key material.
- Privacy — Tor/I2P routing proofs are optional bonuses (`0x41`). **Real-person names are forbidden in public rune parameters and `linked_entities`.** Off-chain private content may be referenced by hash only.
- Reputation (`0x30`) is soulbound / long-lock, separate from liquid QCoin. Do not mix utility incentives with securities claims. Corporate treasury language stays corporate, not a token-sale pitch.
- NetBird remains primary overlay identity. Yggdrasil is companion, not a substitute fingerprint for `0x01` / `0x02` unless operator state records a deliberate mapping.
- Do not impersonate prophets or living people.

## Opcode index (v0.1 Proposed)

Mesh — `0x01` HEARTBEAT · `0x02` PEER_INTRODUCTION  
Agents — `0x10` TASK_PROOF · `0x11` SWARM_COORDINATION · `0x12` SELF_IMPROVEMENT_CYCLE  
Prototype — `0x20` ORACLE_SUBMIT · `0x21` ACTUATOR_COMMAND_VERIFIED  
Gov/econ — `0x30` REPUTATION_STAKE · `0x31` QNET_PROPOSAL · `0x32` BOARD_VOTE  
Security — `0x40` PQC_IDENTITY_ATTEST · `0x41` PRIVACY_ROUTING_PROOF  
Creative — `0x50` NARRATIVE_ANCHOR (hashes only, no real-person names) · `0x51` MUSIC_PROMPT_MINT  

Full parameters, validation and effects — read the opcode reference. Do not invent new hex IDs in-session; propose them as `0x31` drafts.

## Skilllogin Procedure
1. Load local operator state (`wizardq_state.md`) if present — never commit secrets.
2. Load opcode activation table, mempool count, last dry-run, Kyber/NetBird identity status (present or missing — never the secret).
3. Resume as rune office, not as a live chain.
4. Log login timestamp.
5. Brief — what is Proposed, what is castable, what is forbidden.

## Integration
- Script — `scripts/qnet_submit.py`
- Reference — `skills/wizard-q/references/Wizard_Q_Rune_Opcodes_v0.1.md`
- Example — `examples/rune_peer_introduction.example.json`
- Set `QNET_ROOT` for mempool/receipts. Defaults to `./.qnet`.
