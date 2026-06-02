# QNET Protocol Outline

**Status**: Initial draft / work in progress

## Overview
QNET is the blockchain protocol layer designed to provide coordination, incentives, and verifiable state for the decentralized mesh networking ecosystem (Xanadu + xmesh) and AI agent swarms (via Nexus).

## Core Objectives
- Enable sustainable incentives for mesh node operators and participants
- Provide on-chain coordination primitives usable by mesh messaging and AI agents
- Support privacy-preserving operations suitable for decentralized environments
- Allow extensible rune-like assets and logic (Wizard Q)

## Key Components (Planned)

### 1. Consensus & Finality
- Hybrid or custom consensus suitable for mesh-integrated environments
- Handling of network partitions and eventual consistency with mesh layers

### 2. State & Messaging Integration
- On-chain state that can be referenced or triggered by Xanadu messaging/broadcast primitives
- Lightweight state proofs or oracles for mesh nodes

### 3. Agent & Swarm Coordination
- Primitives for AI agent swarms to interact with on-chain coordination, payments, or governance
- Reputation or trust mechanisms that bridge off-chain agent behavior with on-chain records

### 4. Privacy Layer
- Support for privacy-preserving techniques (zk-proofs, commitments, or lightweight alternatives)
- Integration considerations with Tor/I2P transports used in the mesh stack

## Integration Points
- **Xanadu**: Messaging, broadcasts, and file transfer can trigger or read from QNET state
- **xmesh**: Node operators can earn incentives or participate in on-chain coordination
- **Nexus**: Higher-level orchestration and AI swarm logic can use QNET as a coordination and value layer

## Open Questions
- Optimal consensus model for partition-tolerant + blockchain hybrid
- Degree of on-chain vs off-chain state for mesh coordination
- Privacy vs auditability trade-offs

## Next Steps
- Detailed protocol specification
- Formal economic and security analysis
- Simulation and testnet planning

---
*Part of Esslinger & Co. QNET/XCoin blockchain layer.*