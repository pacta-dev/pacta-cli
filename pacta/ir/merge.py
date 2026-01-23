# SPDX-License-Identifier: AGPL-3.0-only
#
# Copyright (c) 2026 Pacta Contributors
#
# This file is part of Pacta.
#
# Pacta is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 only.
#
# Pacta is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.

from collections.abc import Sequence
from typing import Any

from pacta.ir.keys import edge_key, node_key
from pacta.ir.types import ArchitectureIR, IREdge, IRNode


def _merge_metadata(irs: Sequence[ArchitectureIR]) -> dict[str, Any]:
    """
    Merge metadata from multiple IRs in a deterministic, namespaced way.

    Policy:
    - Keep top-level keys from the first IR (if any) under "base".
    - Store each IR's metadata under "sources[{produced_by}]".
    - If produced_by repeats, append an index to make it unique.
    """
    if not irs:
        return {}

    sources: dict[str, Any] = {}
    seen_names: dict[str, int] = {}

    for ir in irs:
        name = ir.produced_by or "unknown"
        if name in sources:
            seen_names[name] = seen_names.get(name, 1) + 1
            name = f"{name}#{seen_names[name]}"
        else:
            seen_names[name] = 1

        sources[name] = dict(ir.metadata or {})

    merged: dict[str, Any] = {
        "base": dict(irs[0].metadata or {}),
        "sources": sources,
    }
    return merged


def _prefer_node(a: IRNode, b: IRNode) -> IRNode:
    """
    Choose the better node representation when two nodes have the same identity.

    Policy:
    - Prefer the node that has path
    - Prefer the node that has loc
    - Prefer the node that has name
    - Prefer the node with more attributes
    - Prefer the node with more tags
    - Prefer the node with enriched fields set (container/layer/context)

    Deterministic tie-break: keep 'a' if equal.
    """

    def score(n: IRNode) -> tuple:
        return (
            1 if n.path else 0,
            1 if n.loc else 0,
            1 if n.name else 0,
            len(n.attributes) if n.attributes else 0,
            len(n.tags) if n.tags else 0,
            1 if n.container else 0,
            1 if n.layer else 0,
            1 if n.context else 0,
        )

    return b if score(b) > score(a) else a


def _prefer_edge(a: IREdge, b: IREdge) -> IREdge:
    """
    Choose the better edge representation when two edges have the same identity.

    Policy:
    - Prefer higher confidence
    - Prefer edge with loc
    - Prefer edge with more details
    - Prefer edge with enriched fields set

    Deterministic tie-break: keep 'a' if equal.
    """

    def score(e: IREdge) -> tuple:
        return (
            float(e.confidence),
            1 if e.loc else 0,
            len(e.details) if e.details else 0,
            1 if e.src_container else 0,
            1 if e.src_layer else 0,
            1 if e.src_context else 0,
            1 if e.dst_container else 0,
            1 if e.dst_layer else 0,
            1 if e.dst_context else 0,
        )

    return b if score(b) > score(a) else a


class DefaultIRMerger:
    """
    Merge multiple ArchitectureIR objects into one.

    Guarantees:
    - Node identity is CanonicalId (node_key)
    - Edge identity is (src,dst,dep_type) hashed (edge_key) by default
    - Merge is deterministic (stable tie-breaking)

    Note:
    - Ordering normalization is typically done later by DefaultIRNormalizer.
    """

    def merge(self, irs: Sequence[ArchitectureIR]) -> ArchitectureIR:
        if not irs:
            # Caller may prefer ArchitectureIR.empty(repo_root), but keep consistent here.
            raise ValueError("DefaultIRMerger.merge() requires at least one IR")

        # If repo roots differ (shouldn't), prefer first.
        repo_root = irs[0].repo_root
        schema_version = max(ir.schema_version for ir in irs)
        produced_by = "pacta-merged"

        # Merge nodes
        nodes_map: dict[str, IRNode] = {}
        for ir in irs:
            for n in ir.nodes:
                k = node_key(n)
                if k in nodes_map:
                    nodes_map[k] = _prefer_node(nodes_map[k], n)
                else:
                    nodes_map[k] = n

        # Merge edges
        edges_map: dict[str, IREdge] = {}
        for ir in irs:
            for e in ir.edges:
                k = edge_key(e, include_location=False, include_details=False)
                if k in edges_map:
                    edges_map[k] = _prefer_edge(edges_map[k], e)
                else:
                    edges_map[k] = e

        merged_nodes = tuple(nodes_map.values())
        merged_edges = tuple(edges_map.values())

        return ArchitectureIR(
            schema_version=schema_version,
            produced_by=produced_by,
            repo_root=repo_root,
            nodes=merged_nodes,
            edges=merged_edges,
            metadata=_merge_metadata(irs),
        )
