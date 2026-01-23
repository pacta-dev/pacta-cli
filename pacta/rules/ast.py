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

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """
    Optional source location for AST nodes (used by parser and errors).
    """

    file: str | None = None
    line: int | None = None
    column: int | None = None

    end_line: int | None = None
    end_column: int | None = None


@dataclass(frozen=True, slots=True)
class RulesDocumentAst:
    """
    Result of parsing a rules file (DSL/YAML/etc.).
    """

    rules: tuple["RuleAst", ...] = ()
    span: SourceSpan | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


SeverityAst = Literal["error", "warning", "info"]
RuleActionAst = Literal["forbid", "allow", "require"]
RuleTargetAst = Literal["dependency", "node"]


@dataclass(frozen=True, slots=True, kw_only=True)
class WhenAst:
    """
    Shared base for "when" blocks.

    target:
      - "dependency": predicates are evaluated against a dependency edge
      - "node": predicates are evaluated against a node
    """

    target: RuleTargetAst
    predicate: "ExprAst"
    span: SourceSpan | None = None


@dataclass(frozen=True, slots=True)
class RuleAst:
    """
    A single rule in source form.
    """

    id: str
    name: str
    description: str | None = None

    severity: SeverityAst = "error"
    action: RuleActionAst = "forbid"

    when: WhenAst | None = None
    except_when: tuple[WhenAst, ...] = ()

    message: str | None = None
    suggestion: str | None = None

    tags: tuple[str, ...] = ()
    span: SourceSpan | None = None

    # arbitrary metadata from frontend
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class DependencyWhenAst(WhenAst):
    """
    Specialized when for dependency edges.
    """

    target: Literal["dependency"] = "dependency"


@dataclass(frozen=True, slots=True, kw_only=True)
class NodeWhenAst(WhenAst):
    """
    Specialized when for nodes.
    """

    target: Literal["node"] = "node"


@dataclass(frozen=True, slots=True)
class ExprAst:
    """
    Base class for predicate expressions.
    """

    span: SourceSpan | None = None


@dataclass(frozen=True, slots=True)
class AndAst(ExprAst):
    items: tuple[ExprAst, ...] = ()


@dataclass(frozen=True, slots=True)
class OrAst(ExprAst):
    items: tuple[ExprAst, ...] = ()


@dataclass(frozen=True, slots=True)
class NotAst(ExprAst):
    item: ExprAst | None = None


LiteralKind = Literal["string", "number", "bool", "list", "null"]


@dataclass(frozen=True, slots=True)
class LiteralAst(ExprAst):
    """
    Literal values used in comparisons.
    """

    kind: LiteralKind = "string"
    value: Any = None


@dataclass(frozen=True, slots=True)
class FieldAst(ExprAst):
    """
    A field reference.

    Node targets:
      - "node.kind", "node.path", "node.name", "node.layer",
        "node.context", "node.container", "node.tags", "node.fqname"

    Dependency targets:
      - "from.layer", "to.layer"
      - "from.context", "to.context"
      - "from.container", "to.container"
      - "from.fqname", "to.fqname"
      - "dep.type"
      - "loc.file" (optional if you want)
    """

    path: str = ""


CompareOp = Literal["==", "!=", "in", "not_in", "glob", "matches", "contains"]


@dataclass(frozen=True, slots=True)
class CompareAst(ExprAst):
    """
    Compare a field to a literal.

    Examples:
      node.layer == "domain"
      from.layer glob "domain.*"
      to.tags contains "internal"
      node.path matches ".*test.*"
      node.kind in ["module", "class"]
    """

    left: FieldAst | None = None
    op: CompareOp = "=="
    right: LiteralAst | None = None
