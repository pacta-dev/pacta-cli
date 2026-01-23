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

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from pacta.ir.types import ArchitectureIR, IREdge, IRNode, SourceLoc, SourcePos


def _norm_path(p: str | None) -> str | None:
    """
    Normalize filesystem-like paths into a stable POSIX form.
    - backslashes -> slashes
    - remove leading './'
    - collapse duplicate slashes
    """
    if p is None:
        return None
    p = p.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    while "//" in p:
        p = p.replace("//", "/")
    return p


def _norm_mapping(m: Mapping[str, Any]) -> dict[str, Any]:
    """
    Return a deterministic copy of mapping:
    - sort keys
    - recursively normalize nested dict/list/tuple
    """

    def norm(v: Any) -> Any:
        if isinstance(v, dict):
            return _norm_mapping(v)
        if isinstance(v, list):
            return [norm(x) for x in v]
        if isinstance(v, tuple):
            return tuple(norm(x) for x in v)
        return v

    return {k: norm(m[k]) for k in sorted(m.keys())}


def _norm_tags(tags: tuple[str, ...]) -> tuple[str, ...]:
    """
    Deterministic tags: stripped, unique, sorted.
    """
    cleaned = [t.strip() for t in tags if t and t.strip()]
    return tuple(sorted(set(cleaned)))


def _clamp_confidence(x: float) -> float:
    if x != x:  # NaN
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def _norm_loc(loc: SourceLoc | None) -> SourceLoc | None:
    if loc is None:
        return None
    file = _norm_path(loc.file) or loc.file
    start = SourcePos(line=int(loc.start.line), column=int(loc.start.column))
    end = None
    if loc.end is not None:
        end = SourcePos(line=int(loc.end.line), column=int(loc.end.column))
    return SourceLoc(file=file, start=start, end=end)


def _node_sort_key(n: IRNode) -> tuple:
    return (
        n.kind.value,
        str(n.id),
        n.path or "",
        n.name or "",
        n.container or "",
        n.layer or "",
        n.context or "",
    )


def _edge_sort_key(e: IREdge) -> tuple:
    loc = e.loc
    if loc is None:
        loc_key = ("", 0, 0)
    else:
        loc_key = (loc.file, loc.start.line, loc.start.column)

    return (
        e.dep_type.value,
        str(e.src),
        str(e.dst),
        loc_key,
        e.src_container or "",
        e.src_layer or "",
        e.src_context or "",
        e.dst_container or "",
        e.dst_layer or "",
        e.dst_context or "",
    )


class DefaultIRNormalizer:
    """
    Deterministic normalization for ArchitectureIR.

    Ensures:
    - stable paths (POSIX)
    - stable tag sets
    - stable ordering of nodes/edges
    - stable ordering/shape of details/attributes/metadata
    - confidence clamped to [0,1]
    """

    def normalize(self, ir: ArchitectureIR) -> ArchitectureIR:
        # normalize nodes
        norm_nodes: list[IRNode] = []
        for n in ir.nodes:
            nn = replace(
                n,
                path=_norm_path(n.path),
                loc=_norm_loc(n.loc),
                tags=_norm_tags(n.tags),
                attributes=_norm_mapping(n.attributes) if n.attributes else {},
            )
            norm_nodes.append(nn)

        # normalize edges
        norm_edges: list[IREdge] = []
        for e in ir.edges:
            ne = replace(
                e,
                loc=_norm_loc(e.loc),
                confidence=_clamp_confidence(e.confidence),
                details=_norm_mapping(e.details) if e.details else {},
            )
            norm_edges.append(ne)

        # normalize metadata
        meta = _norm_mapping(ir.metadata) if ir.metadata else {}

        # deterministic ordering
        norm_nodes_sorted = tuple(sorted(norm_nodes, key=_node_sort_key))
        norm_edges_sorted = tuple(sorted(norm_edges, key=_edge_sort_key))

        return ArchitectureIR(
            schema_version=int(ir.schema_version),
            produced_by=str(ir.produced_by),
            repo_root=_norm_path(str(ir.repo_root)) or str(ir.repo_root),
            nodes=norm_nodes_sorted,
            edges=norm_edges_sorted,
            metadata=meta,
        )
