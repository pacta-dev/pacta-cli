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


def dedupe_nodes(nodes: Iterable[IRNode], *, deterministic: bool = False) -> tuple[IRNode, ...]:
    """
    Dedupe by node_key() with deterministic tie-breaking (keep first).
    Then optionally sort by key for stability.
    """
    seen: dict[str, IRNode] = {}
    for n in nodes:
        k = node_key(n)
        if k not in seen:
            seen[k] = n

    out = list(seen.values())
    if deterministic:
        out.sort(key=lambda n: node_key(n))

    return tuple(out)


def dedupe_edges(
    edges: Iterable[IREdge],
    *,
    include_location: bool = False,
    include_details: bool = False,
    deterministic: bool = False,
) -> tuple[IREdge, ...]:
    """
    Dedupe by edge_key(). Then optionally sort by key for stability.
    """
    seen: dict[str, IREdge] = {}
    for e in edges:
        k = edge_key(e, include_location=include_location, include_details=include_details)
        if k not in seen:
            seen[k] = e

    out = list(seen.values())
    if deterministic:
        out.sort(key=lambda e: edge_key(e, include_location=include_location, include_details=include_details))

    return tuple(out)
