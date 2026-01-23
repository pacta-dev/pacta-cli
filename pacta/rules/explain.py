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
from dataclasses import dataclass
from typing import Any

from pacta.reporting.types import Violation
from pacta.rules.types import Rule, RuleTarget

# Human-readable explanations


def explain_violation(v: Violation) -> str:
    """
    Turn a Violation into a compact explanation suitable for CLI/IDE tooltips.
    """
    ctx = v.context or {}
    target = ctx.get("target")

    if target == "dependency":
        dep_type = ctx.get("dep_type", "?")
        src = ctx.get("src_fqname") or ctx.get("src_id") or "<?>"
        dst = ctx.get("dst_fqname") or ctx.get("dst_id") or "<?>"
        src_layer = ctx.get("src_layer")
        dst_layer = ctx.get("dst_layer")

        parts: list[str] = []
        parts.append(f"Dependency violation ({dep_type}).")
        parts.append(f"{src} -> {dst}")
        if src_layer or dst_layer:
            parts.append(f"layers: {src_layer or '?'} -> {dst_layer or '?'}")
        return " ".join(parts)

    if target == "node":
        ident = ctx.get("fqname") or ctx.get("node_id") or "<?>"
        kind = ctx.get("kind", "?")
        layer = ctx.get("layer")
        context = ctx.get("context")
        container = ctx.get("container")

        parts = [f"Node violation ({kind}): {ident}"]
        extras = []
        if layer:
            extras.append(f"layer={layer}")
        if context:
            extras.append(f"context={context}")
        if container:
            extras.append(f"container={container}")
        if extras:
            parts.append(f"({', '.join(extras)})")
        return " ".join(parts)

    # Fallback
    return v.message


def explain_rule(rule: Rule) -> str:
    """
    Explain a compiled Rule at a high level (for listing rules, debug output).
    """
    target = "dependencies" if rule.target == RuleTarget.DEPENDENCY else "nodes"
    action = rule.action.value.lower()

    base = f"[{rule.id}] {rule.name} — {action} {target} ({rule.severity.value.lower()})"
    if rule.description:
        return f"{base}\n{rule.description}"
    return base


# Optional: "why did it match?" debug helpers (v0)


@dataclass(frozen=True, slots=True)
class PredicateTrace:
    """
    Minimal trace record for debugging predicate evaluation.
    """

    rule_id: str
    matched: bool
    details: Mapping[str, Any]


def trace_violation(v: Violation) -> PredicateTrace:
    """
    v0 trace: just echo violation context.
    Future: include expression tree and extracted field values.
    """
    return PredicateTrace(
        rule_id=v.rule.id,
        matched=True,
        details=v.context or {},
    )
