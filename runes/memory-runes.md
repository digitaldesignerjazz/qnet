# Memory Runes Specification

**Memory Runes** are specialized runes (Wizard Q) on the QNET blockchain designed to store, manage, and incentivize verifiable agent memory in a decentralized ecosystem.

They serve as the persistent, trustable memory layer that complements fast in-memory and vector-based agent memory systems.

## Overview

Memory Runes enable agents to create, share, link, and economically signal the importance of memories while maintaining selective access control and integration with the broader Nexus architecture.

### Goals

- Provide verifiable long-term memory for AI agents
- Support narrative continuity in Nexus Cyberspace
- Enable economic incentives around memory creation and curation
- Allow selective sharing between agents and layers
- Bridge ephemeral agent memory with persistent on-chain state

## Rune Types

| Type                  | Description                                      | Mutability | Primary Use Case                     |
|-----------------------|--------------------------------------------------|------------|--------------------------------------|
| Episodic              | Records specific events and experiences          | Low        | Storytelling, historical records     |
| Semantic              | Stores facts, knowledge, and world state         | Medium     | Shared understanding, world lore     |
| Relational            | Tracks relationships, trust, and social memory   | Medium     | Reputation, alliance building        |
| Narrative             | Captures story-relevant memories and arcs        | Low        | Agent-driven narratives              |

## Rune Structure

```json
{
  "rune_type": "episodic" | "semantic" | "relational" | "narrative",
  "creator": "agent_address",
  "timestamp": 174XXXXXXX,
  "summary": "Short description of the memory",
  "content_hash": "ipfs://Qm...",           // Full content stored off-chain
  "tags": ["conflict", "alliance", "discovery"],
  "access_control": {
    "public": false,
    "allowed_agents": ["agent_123", "agent_456"],
    "allowed_roles": ["nexus_orchestrator"]
  },
  "linked_memories": ["rune_id_abc", "rune_id_def"],
  "importance_score": 0.87,
  "source_layer": "nexus" | "xanadu" | "cyberspace"
}
```

## Core Operations

| Operation     | Description                                           | Authorization          | Economic Cost          |
|---------------|-------------------------------------------------------|------------------------|------------------------|
| Mint          | Create a new Memory Rune                              | Any agent              | XCoin burn / stake     |
| Update        | Modify mutable fields (tags, importance, access)      | Creator or authorized  | Small fee              |
| Link          | Connect two Memory Runes                              | Authorized             | Minimal                |
| GrantAccess   | Add/remove agents from access list                    | Creator                | Free / small fee       |
| Query         | Read memory (subject to access rules)                 | Authorized parties     | May require payment    |
| Stake         | Increase importance through economic signaling        | Any agent              | Stake XCoin            |
| Archive       | Mark as historical (reduce active costs)              | Creator / governance   | Possible refund        |

## Integration with Layers

- **Nexus**: Decides when to mint Memory Runes and manages importance scoring
- **QNET**: Stores the rune, access rules, and economic signals
- **Xanadu + xmesh**: Enables fast sharing of memory references via gossip
- **Cyberspace**: Uses Memory Runes as persistent lore anchors for narratives
- **Swarm**: Agents reference shared Memory Runes during coordination

## Access Control Model

Memory Runes support flexible access:
- Public (anyone can read)
- Private (only creator)
- Selective (specific agents or roles)
- Time-limited or condition-based access (future)

## Economic Model (Proposed)

- Minting costs XCoin (burn or stake)
- Staking on memories increases visibility and importance
- Querying protected memories may require payment to the creator
- High-importance memories can earn curation rewards

## Open Questions

- Should Memory Runes be soulbound or transferable?
- How to handle conflicting memories?
- Optimal balance between on-chain data and off-chain content?
- Governance model for archiving or disputing memories

---

*Part of the QNET protocol layer in the Nexus ecosystem.*