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

from collections.abc import Iterable, Sequence
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, cast

from pacta.snapshot._keys import edge_key, node_key
from pacta.snapshot.types import Snapshot, SnapshotMeta


class DefaultSnapshotBuilder:
    """
    Builds a persisted Snapshot from an in-memory IR structure.

    Expected IR shapes (any one works):
    - ir.nodes, ir.edges (iterables)
    - ir.get_nodes(), ir.get_edges()
    - dict with {"nodes": ..., "edges": ...}
    """

    def __init__(self, *, schema_version: int = 1) -> None:
        self._schema_version = schema_version

    def build(
        self,
        ir: Any,
        *,
        meta: SnapshotMeta,
        model_version: int | None = None,
        violations: Sequence[Any] | None = None,
    ) -> Snapshot:
        nodes = tuple(self._extract_nodes(ir))
        edges = tuple(self._extract_edges(ir))

        # Deterministic ordering
        nodes = tuple(sorted(nodes, key=node_key))
        edges = tuple(sorted(edges, key=edge_key))

        created_at = meta.created_at or datetime.now(timezone.utc).isoformat()
        final_meta = replace(meta, created_at=created_at, model_version=model_version or meta.model_version)

        return Snapshot(
            schema_version=self._schema_version,
            meta=final_meta,
            nodes=nodes,
            edges=edges,
            violations=tuple(violations) if violations else (),
        )

    def _extract_nodes(self, ir: Any) -> Iterable[Any]:
        if isinstance(ir, dict) and "nodes" in ir:
            return cast(Iterable[Any], ir["nodes"])
        if hasattr(ir, "nodes"):
            return cast(Iterable[Any], ir.nodes)
        if hasattr(ir, "get_nodes"):
            return cast(Iterable[Any], ir.get_nodes())
        raise TypeError("IR does not expose nodes (expected .nodes, .get_nodes(), or dict['nodes']).")

    def _extract_edges(self, ir: Any) -> Iterable[Any]:
        if isinstance(ir, dict) and "edges" in ir:
            return cast(Iterable[Any], ir["edges"])
        if hasattr(ir, "edges"):
            return cast(Iterable[Any], ir.edges)
        if hasattr(ir, "get_edges"):
            return cast(Iterable[Any], ir.get_edges())
        raise TypeError("IR does not expose edges (expected .edges, .get_edges(), or dict['edges']).")
