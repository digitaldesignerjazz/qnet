#!/usr/bin/env python3
"""Wizard Q rune envelope: opcode table (v0.1 Proposed) and validation.

Used by scripts/qnet_cli.py (map/validate/skeleton) and node/qnetd.py.
Envelope format (same as qnet_submit.py / qnet_cli.py skeleton):
  opcode, name, version, rune_id, timestamp, parameters, signatures, status

NOTE: signatures are checked for presence only. There is no cryptographic
verification yet (no NetBird/Kyber key material is used here).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

ENVELOPE_KEYS = ["opcode", "name", "version", "rune_id", "timestamp", "parameters", "signatures", "status"]
READY_STATUSES = ("signed-ready", "signed", "ready")
PLACEHOLDER_PREFIX = "TO_BE_FILLED"


def _op(name, band, high_value, required, optional=()):
    return {"name": name, "band": band, "high_value": high_value,
            "required": list(required), "optional": list(optional)}


# Source: skills/wizard-q/references/Wizard_Q_Rune_Opcodes_v0.1.md (status Proposed).
OPCODES: dict[str, dict[str, Any]] = {
    "0x01": _op("RUNE_MESH_HEARTBEAT", "mesh", False,
                ["node_fingerprint", "timestamp", "uptime_seconds", "peer_count"], ["avg_latency_ms", "signature"]),
    "0x02": _op("RUNE_PEER_INTRODUCTION", "mesh", True,
                ["introducer_fingerprint", "new_peer_fingerprint", "connection_proof", "timestamp"]),
    "0x10": _op("RUNE_AGENT_TASK_PROOF", "agents", False,
                ["agent_id", "task_hash", "result_hash", "compute_units"], ["style_flags", "swarm_session_id", "signature"]),
    "0x11": _op("RUNE_SWARM_COORDINATION", "agents", False,
                ["swarm_id", "participating_agents", "coordination_proof", "outcome_quality_score"]),
    "0x12": _op("RUNE_SELF_IMPROVEMENT_CYCLE", "agents", True,
                ["agent_id", "previous_model_hash", "new_model_or_prompt_delta_hash", "performance_delta", "review_signature"]),
    "0x20": _op("RUNE_PROTOTYPE_ORACLE_SUBMIT", "prototype", False,
                ["prototype_id", "sensor_type", "data_payload_hash", "timestamp", "mesh_anchor_fingerprint"], ["signature"]),
    "0x21": _op("RUNE_ACTUATOR_COMMAND_VERIFIED", "prototype", True,
                ["prototype_id", "command_hash", "execution_proof"], ["energy_used"]),
    "0x30": _op("RUNE_REPUTATION_STAKE", "gov", True,
                ["staker_fingerprint", "amount_qcoin", "lock_duration_blocks", "target_layer_mask"]),
    "0x31": _op("RUNE_QNET_PROPOSAL", "gov", True,
                ["proposer_fingerprint", "proposal_hash", "voting_period", "quorum_threshold", "category"]),
    "0x32": _op("RUNE_BOARD_VOTE", "gov", True,
                ["director_fingerprint", "proposal_id", "vote"], ["rationale_hash"]),
    "0x40": _op("RUNE_PQC_IDENTITY_ATTEST", "security", True,
                ["entity_fingerprint", "kyber_pubkey_hash", "classical_pubkey_hash", "attestation_data", "hybrid_signature"]),
    "0x41": _op("RUNE_PRIVACY_ROUTING_PROOF", "security", False,
                ["routing_session_id", "tor_i2p_circuit_proof", "data_volume", "purpose"]),
    "0x50": _op("RUNE_NARRATIVE_ANCHOR", "creative", False,
                ["anchor_type", "content_hash"], ["emotional_valence", "linked_entities", "signature"]),
    "0x51": _op("RUNE_MUSIC_PROMPT_MINT", "creative", False,
                ["prompt_hash", "style_tags", "generation_proof"], ["linked_narrative_anchor"]),
}
NAME_TO_OPCODE = {spec["name"]: hex_id for hex_id, spec in OPCODES.items()}


def rune_hash(rune: dict[str, Any]) -> str:
    """Content hash, identical to qnet_submit.py's receipt content_hash."""
    return hashlib.sha256(json.dumps(rune, sort_keys=True).encode()).hexdigest()


def _empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == "" or value.startswith(PLACEHOLDER_PREFIX)
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def parse_ts(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    ts = datetime.fromisoformat(value)
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def is_valid(rune: Any, allow_draft: bool = False, freshness_s: int | None = None) -> tuple[bool, list[str]]:
    """Schema + signature-presence check. freshness_s=None disables the age check."""
    errors: list[str] = []
    if not isinstance(rune, dict):
        return False, ["rune must be a JSON object"]
    for key in ENVELOPE_KEYS:
        if key not in rune:
            errors.append(f"missing key '{key}'")
    if errors:
        return False, errors

    spec = OPCODES.get(rune["opcode"])
    if spec is None:
        return False, [f"unknown opcode {rune['opcode']!r}"]
    if rune["name"] != spec["name"]:
        errors.append(f"name {rune['name']!r} does not match opcode {rune['opcode']} ({spec['name']})")
    if _empty(rune["rune_id"]):
        errors.append("rune_id empty")

    params = rune["parameters"]
    if not isinstance(params, dict):
        errors.append("parameters must be an object")
    elif not allow_draft:
        for key in spec["required"]:
            if _empty(params.get(key)):
                errors.append(f"parameters.{key} missing or empty")

    try:
        ts = parse_ts(str(rune["timestamp"]))
        if freshness_s is not None:
            age = abs((datetime.now(timezone.utc) - ts).total_seconds())
            if age > freshness_s:
                errors.append(f"timestamp outside freshness window ({age:.0f}s > {freshness_s}s)")
    except ValueError as e:
        errors.append(f"timestamp unparseable: {e}")

    statuses = READY_STATUSES + (("draft",) if allow_draft else ())
    if rune["status"] not in statuses:
        errors.append(f"status {rune['status']!r} not in {list(statuses)}")

    sigs = rune["signatures"]
    if not isinstance(sigs, dict):
        errors.append("signatures must be an object")
    elif not allow_draft:
        if _empty(sigs.get("netbird_signature")) and _empty(sigs.get("yggdrasil_signature")):
            errors.append("netbird_signature missing")
        if spec["high_value"] and _empty(sigs.get("kyber_signature")):
            errors.append("kyber_signature missing (required for high-value opcode)")
    return (not errors), errors
