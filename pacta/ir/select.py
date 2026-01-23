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

import fnmatch
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from pacta.ir.types import DepType, IREdge, IRNode, SymbolKind

# Matching helpers (used by rule compiler/evaluator)


def match_glob(value: str | None, pattern: str) -> bool:
    """
    Glob match with Unix-style wildcards.
    - None never matches
    - case-sensitive by default (consistent across platforms)
    """
    if value is None:
        return False
    return fnmatch.fnmatchcase(value, pattern)


def match_any_glob(value: str | None, patterns: Sequence[str]) -> bool:
    if value is None:
        return False
    return any(fnmatch.fnmatchcase(value, p) for p in patterns)


def match_regex(value: str | None, regex: str) -> bool:
    """
    Regex match using Python re (search).
    - None never matches
    """
    if value is None:
        return False
    return re.search(regex, value) is not None


# Node selection


@dataclass(frozen=True, slots=True)
class NodeFilter:
    kind: SymbolKind | None = None
    container: str | None = None
    layer: str | None = None
    context: str | None = None

    path_glob: str | None = None
    fqname_glob: str | None = None
    name_glob: str | None = None

    has_tag: str | None = None

    def matches(self, n: IRNode) -> bool:
        if self.kind is not None and n.kind != self.kind:
            return False
        if self.container is not None and n.container != self.container:
            return False
        if self.layer is not None and n.layer != self.layer:
            return False
        if self.context is not None and n.context != self.context:
            return False

        if self.path_glob is not None and not match_glob(n.path, self.path_glob):
            return False
        if self.fqname_glob is not None and not match_glob(n.id.fqname, self.fqname_glob):
            return False
        if self.name_glob is not None and not match_glob(n.name, self.name_glob):
            return False

        if self.has_tag is not None and self.has_tag not in (n.tags or ()):
            return False

        return True


def select_nodes(nodes: Iterable[IRNode], flt: NodeFilter | None = None) -> tuple[IRNode, ...]:
    """
    Deterministic selection: preserves incoming order.
    (IRNormalizer should already ensure stable order.)
    """
    if flt is None:
        return tuple(nodes)
    return tuple(n for n in nodes if flt.matches(n))


# Edge selection


@dataclass(frozen=True, slots=True)
class EdgeFilter:
    dep_type: DepType | None = None

    src_container: str | None = None
    src_layer: str | None = None
    src_context: str | None = None

    dst_container: str | None = None
    dst_layer: str | None = None
    dst_context: str | None = None

    # Optional matching by canonical fqname
    src_fqname_glob: str | None = None
    dst_fqname_glob: str | None = None

    # Optional file/path constraints via edge location
    loc_file_glob: str | None = None

    def matches(self, e: IREdge) -> bool:
        if self.dep_type is not None and e.dep_type != self.dep_type:
            return False

        if self.src_container is not None and e.src_container != self.src_container:
            return False
        if self.src_layer is not None and e.src_layer != self.src_layer:
            return False
        if self.src_context is not None and e.src_context != self.src_context:
            return False

        if self.dst_container is not None and e.dst_container != self.dst_container:
            return False
        if self.dst_layer is not None and e.dst_layer != self.dst_layer:
            return False
        if self.dst_context is not None and e.dst_context != self.dst_context:
            return False

        if self.src_fqname_glob is not None and not match_glob(e.src.fqname, self.src_fqname_glob):
            return False
        if self.dst_fqname_glob is not None and not match_glob(e.dst.fqname, self.dst_fqname_glob):
            return False

        if self.loc_file_glob is not None:
            if e.loc is None:
                return False
            if not match_glob(e.loc.file, self.loc_file_glob):
                return False

        return True


def select_edges(edges: Iterable[IREdge], flt: EdgeFilter | None = None) -> tuple[IREdge, ...]:
    """
    Deterministic selection: preserves incoming order.
    (IRNormalizer should already ensure stable order.)
    """
    if flt is None:
        return tuple(edges)
    return tuple(e for e in edges if flt.matches(e))


def where(nodes_or_edges: Iterable, predicate: Callable[[object], bool]) -> tuple:
    """
    Generic filter utility.
    """
    return tuple(x for x in nodes_or_edges if predicate(x))
