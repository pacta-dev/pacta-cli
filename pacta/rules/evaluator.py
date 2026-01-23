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

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from pacta.ir.index import IRIndex, build_index
from pacta.ir.types import ArchitectureIR, IREdge, IRNode
from pacta.reporting.types import ReportLocation, RuleRef, Violation
from pacta.rules.baseline import ViolationKeyStrategy
from pacta.rules.types import Rule, RuleAction, RuleSet, RuleTarget

IRInput = ArchitectureIR | IRIndex


class RuleEvaluatorProtocol(Protocol):
    def evaluate(self, ir: IRInput, rules: RuleSet) -> tuple[Violation, ...]:
        raise NotImplementedError()


# Location helpers


def _node_location(n: IRNode) -> ReportLocation | None:
    if n.loc is None:
        return None
    return ReportLocation(
        file=n.loc.file,
        line=n.loc.start.line,
        column=n.loc.start.column,
        end_line=None if n.loc.end is None else n.loc.end.line,
        end_column=None if n.loc.end is None else n.loc.end.column,
    )


def _edge_location(e: IREdge) -> ReportLocation | None:
    if e.loc is None:
        return None
    return ReportLocation(
        file=e.loc.file,
        line=e.loc.start.line,
        column=e.loc.start.column,
        end_line=None if e.loc.end is None else e.loc.end.line,
        end_column=None if e.loc.end is None else e.loc.end.column,
    )


def _as_index(ir: IRInput) -> IRIndex:
    return ir if isinstance(ir, IRIndex) else build_index(ir)


def _excluded_by_exception(obj: object, except_when: Sequence) -> bool:
    """
    If ANY exception predicate matches -> exclude object (no violation).
    """
    for ex in except_when:
        try:
            if ex(obj):
                return True
        except Exception:
            # fail-safe: ignore bad exception predicate
            continue
    return False


def _rule_ref(rule: Rule) -> RuleRef:
    return RuleRef(id=rule.id, name=rule.name, severity=rule.severity)


# Evaluator


@dataclass(frozen=True, slots=True)
class DefaultRuleEvaluator(RuleEvaluatorProtocol):
    """
    Evaluates compiled RuleSet against IR (or IRIndex) and produces Violations.

    Semantics:
    - FORBID: each match -> violation
    - REQUIRE: if no matches -> single violation (rule-level)
    - ALLOW: v0 no-op (reserved for allowlist policies)
    """

    key_strategy: ViolationKeyStrategy = ViolationKeyStrategy()

    def evaluate(self, ir: IRInput, rules: RuleSet) -> tuple[Violation, ...]:
        idx = _as_index(ir)
        out: list[Violation] = []

        for rule in rules.rules:
            if rule.target == RuleTarget.NODE:
                out.extend(self._eval_node_rule(idx, rule))
            elif rule.target == RuleTarget.DEPENDENCY:
                out.extend(self._eval_edge_rule(idx, rule))

        return tuple(out)

    def _eval_node_rule(self, idx: IRIndex, rule: Rule) -> list[Violation]:
        matches: list[IRNode] = []

        for n in idx.nodes:
            try:
                if rule.when(n) and not _excluded_by_exception(n, rule.except_when):
                    matches.append(n)
            except Exception:
                continue

        if rule.action == RuleAction.REQUIRE:
            if not matches:
                v = self._require_missing_violation(rule, target="node")
                return [v]
            return []

        if rule.action == RuleAction.ALLOW:
            return []

        # FORBID
        violations: list[Violation] = []
        rr = _rule_ref(rule)

        for n in matches:
            ctx = {
                "target": "node",
                "node_id": str(n.id),
                "fqname": n.id.fqname,
                "kind": n.kind.value,
                "path": n.path,
                "container": n.container,
                "layer": n.layer,
                "context": n.context,
            }
            v = Violation(
                rule=rr,
                message=rule.message,
                location=_node_location(n),
                context=ctx,
                suggestion=rule.suggestion,
            )
            # assign stable key for baselines
            v = self._with_key(v)
            violations.append(v)

        return violations

    def _eval_edge_rule(self, idx: IRIndex, rule: Rule) -> list[Violation]:
        matches: list[IREdge] = []

        for e in idx.edges:
            try:
                if rule.when(e) and not _excluded_by_exception(e, rule.except_when):
                    matches.append(e)
            except Exception:
                continue

        if rule.action == RuleAction.REQUIRE:
            if not matches:
                v = self._require_missing_violation(rule, target="dependency")
                return [v]
            return []

        if rule.action == RuleAction.ALLOW:
            return []

        # FORBID
        violations: list[Violation] = []
        rr = _rule_ref(rule)

        for e in matches:
            ctx = {
                "target": "dependency",
                "dep_type": e.dep_type.value,
                "src_id": str(e.src),
                "dst_id": str(e.dst),
                "src_fqname": e.src.fqname,
                "dst_fqname": e.dst.fqname,
                "src_container": e.src_container,
                "src_layer": e.src_layer,
                "src_context": e.src_context,
                "dst_container": e.dst_container,
                "dst_layer": e.dst_layer,
                "dst_context": e.dst_context,
            }
            v = Violation(
                rule=rr,
                message=rule.message,
                location=_edge_location(e),
                context=ctx,
                suggestion=rule.suggestion,
            )
            v = self._with_key(v)
            violations.append(v)

        return violations

    def _require_missing_violation(self, rule: Rule, *, target: str) -> Violation:
        rr = _rule_ref(rule)
        ctx = {"target": target, "action": "require"}
        v = Violation(
            rule=rr,
            message=rule.message or f"Required {target} pattern not found.",
            location=None,
            context=ctx,
            suggestion=rule.suggestion,
        )
        return self._with_key(v)

    def _with_key(self, v: Violation) -> Violation:
        # Violation is frozen -> use dataclasses.replace pattern via constructor:
        key = self.key_strategy.key_for(v)
        return Violation(
            rule=v.rule,
            message=v.message,
            status=v.status,
            location=v.location,
            context=v.context,
            violation_key=key,
            suggestion=v.suggestion,
        )
