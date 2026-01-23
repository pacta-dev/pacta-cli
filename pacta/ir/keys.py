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

import hashlib
from collections.abc import Iterable
from typing import Any

from pacta.ir.types import IREdge, IRNode

# Helpers


def _stable_str(value: Any) -> str:
    """
    Convert arbitrary values to a stable string representation.

    Rules:
    - dicts are sorted by key
    - iterables are ordered
    - None becomes empty string
    """
    if value is None:
        return ""
    if isinstance(value, dict):
        return ",".join(f"{k}={_stable_str(v)}" for k, v in sorted(value.items()))
    if isinstance(value, (list, tuple, set)):
        return ",".join(_stable_str(v) for v in value)
    return str(value)


def _hash(parts: Iterable[str]) -> str:
    """
    Produce a short, stable hash from string parts.
    """
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()


# Node keys


def node_key(node: IRNode) -> str:
    """
    Stable identity key for an IRNode.

    Uses only canonical identity, NOT mutable/enriched fields.

    Why:
    - node identity must not change when mapping adds container/layer
    - snapshots must diff cleanly
    """
    return str(node.id)


# Edge keys


def edge_key(
    edge: IREdge,
    *,
    include_location: bool = False,
    include_details: bool = False,
) -> str:
    """
    Stable identity key for an IREdge.

    Parameters:
    - include_location:
        If True, line/column are part of identity (stricter).
        If False (default), location is ignored.
    - include_details:
        Whether to include edge.details in identity.

    Default behavior:
    - identity = (src, dst, dep_type)
    """

    parts: list[str] = [
        str(edge.src),
        str(edge.dst),
        edge.dep_type.value,
    ]

    if include_location and edge.loc is not None:
        parts.append(edge.loc.file)
        parts.append(str(edge.loc.start.line))
        parts.append(str(edge.loc.start.column))

    if include_details and edge.details:
        parts.append(_stable_str(edge.details))

    return _hash(parts)


# Batch helpers


def dedupe_nodes(nodes: Iterable[IRNode]) -> tuple[IRNode, ...]:
    """
    Deduplicate nodes by node_key(), keeping first occurrence.
    """
    seen: set[str] = set()
    result: list[IRNode] = []

    for n in nodes:
        k = node_key(n)
        if k not in seen:
            seen.add(k)
            result.append(n)

    return tuple(result)


def dedupe_edges(
    edges: Iterable[IREdge],
    *,
    include_location: bool = False,
    include_details: bool = False,
) -> tuple[IREdge, ...]:
    """
    Deduplicate edges by edge_key().
    """
    seen: set[str] = set()
    result: list[IREdge] = []

    for e in edges:
        k = edge_key(
            e,
            include_location=include_location,
            include_details=include_details,
        )
        if k not in seen:
            seen.add(k)
            result.append(e)

    return tuple(result)
