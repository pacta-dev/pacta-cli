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

from dataclasses import dataclass, replace

from pacta.ir.select import match_any_glob
from pacta.ir.types import ArchitectureIR, IREdge, IRNode
from pacta.model.types import ArchitectureModel


@dataclass(frozen=True, slots=True)
class DefaultArchitectureEnricher:
    """
    Enriches ArchitectureIR nodes and edges with high-level architecture metadata.

    Maps code-level artifacts (files, modules, classes) to:
      - container_id  (which service/component owns this code)
      - layer_id      (ui/application/domain/infra)
      - context_id    (bounded context in DDD)
      - tags          (inherited from container)

    The enrichment process:
      1. For each node: determine container via path matching
      2. For each node: determine layer via glob pattern matching
      3. For each node: lookup context from container
      4. For each edge: enrich src/dst fields by copying from nodes

    This is a critical step in the pipeline:
      - Input:  ArchitectureIR with raw code structure
      - Output: ArchitectureIR with architectural annotations
      - Used by: Rules engine, snapshot builder, reporting
    """

    def enrich(self, ir: ArchitectureIR, model: ArchitectureModel) -> ArchitectureIR:
        """
        Enrich IR with architecture metadata from model.

        Returns a new ArchitectureIR with enriched nodes and edges.
        Original IR is not mutated (immutable dataclasses).
        """
        # Enrich nodes
        enriched_nodes = tuple(self._enrich_node(n, model) for n in ir.nodes)

        # Build lookup with enriched nodes for edge enrichment
        enriched_node_lookup = {str(n.id): n for n in enriched_nodes}

        # Enrich edges using enriched nodes
        enriched_edges = tuple(self._enrich_edge(e, enriched_node_lookup) for e in ir.edges)

        return replace(
            ir,
            nodes=enriched_nodes,
            edges=enriched_edges,
        )

    def _enrich_node(self, node: IRNode, model: ArchitectureModel) -> IRNode:
        """
        Enrich a single node with container, layer, context, and tags.
        """
        # Determine container by matching node.path against container roots
        container_id = self._match_container(node, model)

        # Determine layer by matching node.path against layer patterns
        layer_id = None
        tags: tuple[str, ...] = ()

        if container_id is not None:
            container = model.get_container(container_id)
            if container is not None:
                layer_id = self._match_layer(node, container_id, model)
                tags = container.tags

        # Determine context from container
        context_id = None
        if container_id is not None:
            context_id = model.get_context_for_container(container_id)

        # Return enriched node if anything changed, otherwise return original
        if (
            node.container == container_id
            and node.layer == layer_id
            and node.context == context_id
            and node.tags == tags
        ):
            return node

        return replace(
            node,
            container=container_id,
            layer=layer_id,
            context=context_id,
            tags=tags,
        )

    def _match_container(self, node: IRNode, model: ArchitectureModel) -> str | None:
        """
        Match node path to container roots.

        Strategy:
          - Check if node.path starts with any container's root path
          - Prefer longest match (most specific)
          - Return container_id or None
        """
        if node.path is None:
            return None

        # Normalize path for comparison (forward slashes, no leading ./)
        normalized_path = self._normalize_path(node.path)

        best_match: tuple[str, int] | None = None  # (container_id, root_length)

        for container_id, roots in model.path_roots.items():
            for root in roots:
                # Normalize root as well
                normalized_root = self._normalize_path(root)

                # Check if path starts with root
                # Match must be exact prefix (either full match or followed by /)
                if normalized_path == normalized_root:
                    root_len = len(normalized_root)
                    if best_match is None or root_len > best_match[1]:
                        best_match = (container_id, root_len)
                elif normalized_path.startswith(normalized_root + "/"):
                    root_len = len(normalized_root)
                    if best_match is None or root_len > best_match[1]:
                        best_match = (container_id, root_len)

        return best_match[0] if best_match is not None else None

    def _match_layer(self, node: IRNode, container_id: str, model: ArchitectureModel) -> str | None:
        """
        Match node path to layer patterns within a container.

        Strategy:
          - Check if node.path matches any layer's glob patterns
          - Return first matching layer_id (order matters: should be deterministic)
          - Return None if no match
        """
        if node.path is None:
            return None

        layer_patterns = model.get_layer_patterns(container_id)
        if not layer_patterns:
            return None

        # Normalize path for comparison
        normalized_path = self._normalize_path(node.path)

        # Check each layer in deterministic order (already sorted by resolver)
        for layer_id, patterns in layer_patterns.items():
            if match_any_glob(normalized_path, patterns):
                return layer_id

        return None

    def _enrich_edge(self, edge: IREdge, node_lookup: dict[str, IRNode]) -> IREdge:
        """
        Enrich edge with src/dst container, layer, context from nodes.
        """
        src_node = node_lookup.get(str(edge.src))
        dst_node = node_lookup.get(str(edge.dst))

        src_container = src_node.container if src_node else None
        src_layer = src_node.layer if src_node else None
        src_context = src_node.context if src_node else None

        dst_container = dst_node.container if dst_node else None
        dst_layer = dst_node.layer if dst_node else None
        dst_context = dst_node.context if dst_node else None

        # Return enriched edge if anything changed
        if (
            edge.src_container == src_container
            and edge.src_layer == src_layer
            and edge.src_context == src_context
            and edge.dst_container == dst_container
            and edge.dst_layer == dst_layer
            and edge.dst_context == dst_context
        ):
            return edge

        return replace(
            edge,
            src_container=src_container,
            src_layer=src_layer,
            src_context=src_context,
            dst_container=dst_container,
            dst_layer=dst_layer,
            dst_context=dst_context,
        )

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path for matching:
          - Forward slashes only
          - Strip leading "./"
          - Remove trailing slashes
        """
        s = path.strip().replace("\\", "/")
        while s.startswith("./"):
            s = s[2:]
        return s.rstrip("/") if s != "/" else s
