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

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pacta.reporting.types import Severity
from pacta.rules.ast import SourceSpan

# Enums


class RuleTarget(str, Enum):
    NODE = "node"
    DEPENDENCY = "dependency"


class RuleAction(str, Enum):
    FORBID = "forbid"
    ALLOW = "allow"
    REQUIRE = "require"


# Runtime types

PredicateFn = Callable[[object], bool]


@dataclass(frozen=True, slots=True)
class Rule:
    """
    Compiled rule ready for evaluation.

    - `when` is a callable predicate compiled from AST.
    - `except_when` is a list of predicates; if any matches -> exclude.
    """

    id: str
    name: str

    description: str | None = None
    severity: Severity = Severity.ERROR
    action: RuleAction = RuleAction.FORBID
    target: RuleTarget = RuleTarget.DEPENDENCY

    when: PredicateFn = lambda _: True
    except_when: tuple[PredicateFn, ...] = ()

    message: str = ""
    suggestion: str | None = None
    tags: tuple[str, ...] = ()

    # For UX/debugging: preserve source location
    span: SourceSpan | None = None

    # arbitrary frontend metadata (e.g., original DSL fragment)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RuleSet:
    """
    A compiled set of rules to be applied to a project IR.
    """

    rules: tuple[Rule, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
