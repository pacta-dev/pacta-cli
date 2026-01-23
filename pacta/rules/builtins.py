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

from collections.abc import Callable, Sequence
from typing import Any

from pacta.ir.select import match_glob, match_regex
from pacta.ir.types import IREdge, IRNode

# Value normalization helpers


def as_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    return [value]


def normalize_ws(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()


# Matchers


def glob_match(value: Any, pattern: str) -> bool:
    v = as_str(value)
    if v is None:
        return False
    return match_glob(v, pattern)


def regex_match(value: Any, pattern: str) -> bool:
    v = as_str(value)
    if v is None:
        return False
    return match_regex(v, pattern)


def contains(container: Any, item: Any) -> bool:
    """
    Generic 'contains' semantics:
    - for list/tuple/set: item in container
    - for dict: item in keys
    - for string: substring check
    """
    if container is None:
        return False

    if isinstance(container, (list, tuple, set)):
        return item in container

    if isinstance(container, dict):
        return item in container.keys()

    return str(item) in str(container)


def in_list(value: Any, candidates: Any) -> bool:
    """
    'value in candidates' with safe coercions.
    """
    if candidates is None:
        return False
    if isinstance(candidates, (list, tuple, set)):
        return value in candidates
    # allow comma-separated strings
    if isinstance(candidates, str):
        parts = [p.strip() for p in candidates.split(",") if p.strip()]
        return str(value) in parts
    return False


# Field extraction (runtime)


def get_node_field(node: IRNode, path: str) -> Any:
    """
    Runtime field extraction for node predicates.

    Supported paths:
      - kind, path, name, layer, context, container, tags
      - fqname (node.id.fqname)
      - id (str(node.id))
      - code_root (node.id.code_root)
      - language (node.id.language.value)
    """
    p = path.strip()
    if p.startswith("node."):
        p = p[len("node.") :]

    if p == "kind":
        return node.kind.value
    if p == "path":
        return node.path
    if p == "name":
        return node.name
    if p == "layer":
        return node.layer
    if p == "context":
        return node.context
    if p == "container":
        return node.container
    if p == "tags":
        return node.tags

    if p == "fqname":
        return node.id.fqname
    if p == "id":
        return str(node.id)
    if p == "code_root":
        return node.id.code_root
    if p == "language":
        return node.id.language.value

    raise KeyError(f"Unknown node field: {path}")


def get_edge_field(edge: IREdge, path: str) -> Any:
    """
    Runtime field extraction for dependency predicates.

    Supported paths:
      - from.layer / to.layer
      - from.context / to.context
      - from.container / to.container
      - from.fqname / to.fqname
      - from.id / to.id
      - dep.type
      - loc.file
    """
    p = path.strip()

    if p == "from.layer":
        return edge.src_layer
    if p == "to.layer":
        return edge.dst_layer

    if p == "from.context":
        return edge.src_context
    if p == "to.context":
        return edge.dst_context

    if p == "from.container":
        return edge.src_container
    if p == "to.container":
        return edge.dst_container

    if p == "from.fqname":
        return edge.src.fqname
    if p == "to.fqname":
        return edge.dst.fqname

    if p == "from.id":
        return str(edge.src)
    if p == "to.id":
        return str(edge.dst)

    if p == "dep.type":
        return edge.dep_type.value

    if p == "loc.file":
        return None if edge.loc is None else edge.loc.file

    raise KeyError(f"Unknown dependency field: {path}")


# Composition helpers (useful for compiler or evaluator)

Predicate = Callable[[Any], bool]


def all_of(preds: Sequence[Predicate]) -> Predicate:
    return lambda obj: all(p(obj) for p in preds)


def any_of(preds: Sequence[Predicate]) -> Predicate:
    return lambda obj: any(p(obj) for p in preds)


def not_(pred: Predicate) -> Predicate:
    return lambda obj: not pred(obj)
