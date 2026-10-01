"""
Idempotent Graph Ingestion:
Diffs two snapshots of an identity graph/tree (nodes & edges)
and generates a minimal, deterministic set of idempotent mutation operations:
  - ADD: create node or edge if not present in previous snapshot
  - UPDATE: modify changed properties/attributes on existing node/edge
  - MARK_STALE: soft-delete or flag missing resources rather than destructive drops
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class OperationType(str, Enum):
    ADD = "ADD"
    UPDATE = "UPDATE"
    MARK_STALE = "MARK_STALE"


@dataclass(frozen=True)
class IdentityNode:
    id: str  # Unique identifier (e.g. UPN, ARN, DN, or UUID)
    node_type: str  # e.g., 'User', 'Group', 'Role', 'Policy'
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IdentityEdge:
    source_id: str
    target_id: str
    relationship: str  # e.g., 'MEMBER_OF', 'ASSIGNED_ROLE', 'INHERITS'
    properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> Tuple[str, str, str]:
        return (self.source_id, self.relationship, self.target_id)


@dataclass
class IdentityGraphSnapshot:
    nodes: Dict[str, IdentityNode] = field(default_factory=dict)
    edges: Dict[Tuple[str, str, str], IdentityEdge] = field(default_factory=dict)

    def add_node(self, node: IdentityNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: IdentityEdge) -> None:
        self.edges[edge.key] = edge


@dataclass(frozen=True)
class GraphMutationInstruction:
    operation: OperationType
    target: str  # "NODE" | "EDGE"
    identifier: str
    diff_payload: Dict[str, Any]


class IdempotentGraphDiffer:
    """
    Computes a minimal, ordered sequence of idempotent graph mutations
    between a previous snapshot (T0) and a current snapshot (T1).
    """

    @staticmethod
    def diff(
        previous: IdentityGraphSnapshot,
        current: IdentityGraphSnapshot,
    ) -> List[GraphMutationInstruction]:
        instructions: List[GraphMutationInstruction] = []

        # --- 1. Node Ingestion ---
        prev_node_ids = set(previous.nodes.keys())
        curr_node_ids = set(current.nodes.keys())

        # 1a. ADD new nodes (Must precede edge creation)
        for node_id in sorted(curr_node_ids - prev_node_ids):
            node = current.nodes[node_id]
            instructions.append(
                GraphMutationInstruction(
                    operation=OperationType.ADD,
                    target="NODE",
                    identifier=node_id,
                    diff_payload={
                        "node_type": node.node_type,
                        "properties": node.properties,
                    },
                )
            )

        # 1b. UPDATE existing nodes if payload/type changed
        for node_id in sorted(curr_node_ids & prev_node_ids):
            old_node = previous.nodes[node_id]
            new_node = current.nodes[node_id]

            changed_props = {}
            for k, v in new_node.properties.items():
                if old_node.properties.get(k) != v:
                    changed_props[k] = v

            # Detect cleared/removed properties
            removed_keys = [k for k in old_node.properties if k not in new_node.properties]
            for k in removed_keys:
                changed_props[k] = None

            if old_node.node_type != new_node.node_type or changed_props:
                payload: Dict[str, Any] = {}
                if old_node.node_type != new_node.node_type:
                    payload["node_type"] = new_node.node_type
                if changed_props:
                    payload["properties"] = changed_props

                instructions.append(
                    GraphMutationInstruction(
                        operation=OperationType.UPDATE,
                        target="NODE",
                        identifier=node_id,
                        diff_payload=payload,
                    )
                )

        # 1c. MARK_STALE nodes removed in current snapshot
        for node_id in sorted(prev_node_ids - curr_node_ids):
            instructions.append(
                GraphMutationInstruction(
                    operation=OperationType.MARK_STALE,
                    target="NODE",
                    identifier=node_id,
                    diff_payload={"is_stale": True, "stale_from_snapshot": True},
                )
            )

        # --- 2. Edge Ingestion ---
        prev_edge_keys = set(previous.edges.keys())
        curr_edge_keys = set(current.edges.keys())

        # 2a. ADD new edges
        for edge_key in sorted(curr_edge_keys - prev_edge_keys):
            edge = current.edges[edge_key]
            edge_id_str = f"{edge.source_id}-[{edge.relationship}]->{edge.target_id}"
            instructions.append(
                GraphMutationInstruction(
                    operation=OperationType.ADD,
                    target="EDGE",
                    identifier=edge_id_str,
                    diff_payload={
                        "source": edge.source_id,
                        "relationship": edge.relationship,
                        "target": edge.target_id,
                        "properties": edge.properties,
                    },
                )
            )

        # 2b. UPDATE existing edges if properties changed
        for edge_key in sorted(curr_edge_keys & prev_edge_keys):
            old_edge = previous.edges[edge_key]
            new_edge = current.edges[edge_key]

            changed_edge_props = {
                k: v
                for k, v in new_edge.properties.items()
                if old_edge.properties.get(k) != v
            }
            for k in old_edge.properties:
                if k not in new_edge.properties:
                    changed_edge_props[k] = None

            if changed_edge_props:
                edge_id_str = f"{new_edge.source_id}-[{new_edge.relationship}]->{new_edge.target_id}"
                instructions.append(
                    GraphMutationInstruction(
                        operation=OperationType.UPDATE,
                        target="EDGE",
                        identifier=edge_id_str,
                        diff_payload={"properties": changed_edge_props},
                    )
                )

        # 2c. MARK_STALE removed edges
        for edge_key in sorted(prev_edge_keys - curr_edge_keys):
            edge = previous.edges[edge_key]
            edge_id_str = f"{edge.source_id}-[{edge.relationship}]->{edge.target_id}"
            instructions.append(
                GraphMutationInstruction(
                    operation=OperationType.MARK_STALE,
                    target="EDGE",
                    identifier=edge_id_str,
                    diff_payload={"is_stale": True},
                )
            )

        return instructions


def create_sample_snapshots() -> Tuple[IdentityGraphSnapshot, IdentityGraphSnapshot]:
    # --- Snapshot T0 (Baseline) ---
    t0 = IdentityGraphSnapshot()

    # Nodes
    t0.add_node(IdentityNode("u:alice", "User", {"email": "alice@corp.internal", "department": "SecOps", "status": "active"}))
    t0.add_node(IdentityNode("u:bob", "User", {"email": "bob@corp.internal", "department": "Engineering", "status": "active"}))
    t0.add_node(IdentityNode("u:charlie", "User", {"email": "charlie@corp.internal", "department": "Contractor", "status": "active"}))
    t0.add_node(IdentityNode("g:dev_admins", "Group", {"tier": "Tier-1"}))
    t0.add_node(IdentityNode("r:cloud_admin", "Role", {"scope": "global"}))

    # Edges
    t0.add_edge(IdentityEdge("u:alice", "g:dev_admins", "MEMBER_OF", {"assigned_by": "secops"}))
    t0.add_edge(IdentityEdge("u:bob", "g:dev_admins", "MEMBER_OF", {"assigned_by": "lead"}))
    t0.add_edge(IdentityEdge("u:charlie", "r:cloud_admin", "ASSIGNED_ROLE", {"ttl_hours": 24}))
    t0.add_edge(IdentityEdge("g:dev_admins", "r:cloud_admin", "ASSIGNED_ROLE", {}))

    # --- Snapshot T1 (Updated Directory State) ---
    # Changes:
    # 1. ADD: New node "u:david", new edge "u:david" -> "g:dev_admins"
    # 2. UPDATE: "u:bob" shifted from Engineering to Arch; edge u:alice->g:dev_admins gets 'mfa_enforced'=True
    # 3. MARK_STALE: "u:charlie" deactivated/missing; "u:charlie"->role edge removed
    t1 = IdentityGraphSnapshot()

    t1.add_node(IdentityNode("u:alice", "User", {"email": "alice@corp.internal", "department": "SecOps", "status": "active"}))
    # Bob updated department
    t1.add_node(IdentityNode("u:bob", "User", {"email": "bob@corp.internal", "department": "AI Architecture", "status": "active"}))
    # Charlie is gone from directory
    # David is newly onboarded
    t1.add_node(IdentityNode("u:david", "User", {"email": "david@corp.internal", "department": "Engineering", "status": "active"}))
    t1.add_node(IdentityNode("g:dev_admins", "Group", {"tier": "Tier-1"}))
    t1.add_node(IdentityNode("r:cloud_admin", "Role", {"scope": "global"}))

    # Alice membership edge properties updated
    t1.add_edge(IdentityEdge("u:alice", "g:dev_admins", "MEMBER_OF", {"assigned_by": "secops", "mfa_enforced": True}))
    t1.add_edge(IdentityEdge("u:bob", "g:dev_admins", "MEMBER_OF", {"assigned_by": "lead"}))
    # Charlie edge dropped
    # David added to dev_admins
    t1.add_edge(IdentityEdge("u:david", "g:dev_admins", "MEMBER_OF", {"assigned_by": "lead"}))
    t1.add_edge(IdentityEdge("g:dev_admins", "r:cloud_admin", "ASSIGNED_ROLE", {}))

    return t0, t1


def main():
    t0, t1 = create_sample_snapshots()

    differ = IdempotentGraphDiffer()
    instructions = differ.diff(t0, t1)

    print(f"Computed {len(instructions)} idempotent mutations:")
    print("=" * 70)
    for idx, inst in enumerate(instructions, 1):
        op = f"[{inst.operation.value}]".ljust(13)
        target = f"[{inst.target}]".ljust(8)
        payload = json.dumps(inst.diff_payload)
        print(f"{idx:02d}. {op} {target} ID: {inst.identifier:<35} | Diff: {payload}")


if __name__ == "__main__":
    main()