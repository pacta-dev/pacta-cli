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

from typing import Any

from pacta.snapshot._keys import edge_key, node_key
from pacta.snapshot.jsonutil import dumps_deterministic
from pacta.snapshot.types import Snapshot, SnapshotDiff


def _signature(obj: Any) -> str:
    # A deterministic “content signature” for change detection.
    if hasattr(obj, "to_dict"):
        return dumps_deterministic(obj.to_dict())
    if hasattr(obj, "__dict__"):
        return dumps_deterministic(vars(obj))
    return repr(obj)


class DefaultSnapshotDiffEngine:
    """
    Pure structural diff. Rule-agnostic.
    """

    def diff(self, before: Snapshot, after: Snapshot, *, include_details: bool = True) -> SnapshotDiff:
        before_nodes = {node_key(n): _signature(n) for n in before.nodes}
        after_nodes = {node_key(n): _signature(n) for n in after.nodes}

        before_edges = {edge_key(e): _signature(e) for e in before.edges}
        after_edges = {edge_key(e): _signature(e) for e in after.edges}

        added_nodes = sorted(set(after_nodes) - set(before_nodes))
        removed_nodes = sorted(set(before_nodes) - set(after_nodes))
        common_nodes = set(before_nodes) & set(after_nodes)
        changed_nodes = sorted(k for k in common_nodes if before_nodes[k] != after_nodes[k])

        added_edges = sorted(set(after_edges) - set(before_edges))
        removed_edges = sorted(set(before_edges) - set(after_edges))
        common_edges = set(before_edges) & set(after_edges)
        changed_edges = sorted(k for k in common_edges if before_edges[k] != after_edges[k])

        details: dict[str, Any] = {}
        if include_details:
            details = {
                "nodes": {
                    "added": added_nodes,
                    "removed": removed_nodes,
                    "changed": changed_nodes,
                },
                "edges": {
                    "added": added_edges,
                    "removed": removed_edges,
                    "changed": changed_edges,
                },
            }

        return SnapshotDiff(
            nodes_added=len(added_nodes),
            nodes_removed=len(removed_nodes),
            edges_added=len(added_edges),
            edges_removed=len(removed_edges),
            details=details,
        )
