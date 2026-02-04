from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from pacta.ir.select import match_glob, match_regex
from pacta.ir.types import IREdge, IRNode
from pacta.reporting.types import Severity
from pacta.rules.ast import (
    AndAst,
    CompareAst,
    ExprAst,
    FieldAst,
    LiteralAst,
    NotAst,
    OrAst,
    RuleAst,
    RulesDocumentAst,
    WhenAst,
)
from pacta.rules.errors import RulesCompileError
from pacta.rules.types import Rule, RuleAction, RuleSet, RuleTarget

# Internal types

PredicateFn = Callable[[object], bool]


@dataclass(frozen=True, slots=True)
class _CompiledWhen:
    target: RuleTarget
    predicate: PredicateFn


def _get_node_field(n: IRNode, field: str) -> Any:
    """
    Supported node fields (frontends may use either node.<x> or <x>):
      - symbol_kind (SymbolKind.value — file, module, class, etc.)
      - kind (immediate container kind — service, module, library)
      - within (top-level container's kind — for nested containers)
      - service (top-level container ancestor)
      - path
      - name
      - layer
      - context
      - container
      - tags (tuple[str,...])
      - fqname (n.id.fqname)
      - id (str(n.id))
      - code_root (n.id.code_root)
      - language (n.id.language.value)
    """
    f = field
    if f.startswith("node."):
        f = f[len("node.") :]

    if f == "symbol_kind":
        return n.kind.value
    if f == "kind":
        return n.container_kind
    if f == "within":
        return n.within
    if f == "service":
        return n.service
    if f == "path":
        return n.path
    if f == "name":
        return n.name
    if f == "layer":
        return n.layer
    if f == "context":
        return n.context
    if f == "container":
        return n.container
    if f == "tags":
        return n.tags
    if f in ("fqname", "id.fqname"):
        return n.id.fqname
    if f == "id":
        return str(n.id)
    if f == "code_root":
        return n.id.code_root
    if f == "language":
        return n.id.language.value

    raise KeyError(f"Unknown node field: {field}")


def _get_edge_field(e: IREdge, field: str) -> Any:
    """
    Supported dependency fields:
      - from.layer / to.layer
      - from.context / to.context
      - from.container / to.container
      - from.service / to.service
      - from.kind / to.kind (immediate container kind)
      - from.within / to.within (top-level container's kind)
      - from.fqname / to.fqname
      - from.id / to.id  (full canonical id string)
      - dep.type (DepType.value)
      - loc.file (if loc is present)
    """
    f = field.strip()

    if f == "from.layer":
        return e.src_layer
    if f == "to.layer":
        return e.dst_layer

    if f == "from.context":
        return e.src_context
    if f == "to.context":
        return e.dst_context

    if f == "from.container":
        return e.src_container
    if f == "to.container":
        return e.dst_container

    if f == "from.service":
        return e.src_service
    if f == "to.service":
        return e.dst_service

    if f == "from.kind":
        return e.src_container_kind
    if f == "to.kind":
        return e.dst_container_kind

    if f == "from.within":
        return e.src_within
    if f == "to.within":
        return e.dst_within

    if f == "from.fqname":
        return e.src.fqname
    if f == "to.fqname":
        return e.dst.fqname

    if f == "from.id":
        return str(e.src)
    if f == "to.id":
        return str(e.dst)

    if f == "dep.type":
        return e.dep_type.value

    if f == "loc.file":
        return None if e.loc is None else e.loc.file

    raise KeyError(f"Unknown dependency field: {field}")


# Literal coercion


def _lit_value(lit: LiteralAst) -> Any:
    return lit.value


# Operators


def _op_eq(left: Any, right: Any) -> bool:
    return left == right


def _op_neq(left: Any, right: Any) -> bool:
    return left != right


def _op_in(left: Any, right: Any) -> bool:
    # left in right
    if right is None:
        return False
    if isinstance(right, (list, tuple, set)):
        return left in right
    # allow string "a,b,c"
    if isinstance(right, str):
        return str(left) in right
    return False


def _op_not_in(left: Any, right: Any) -> bool:
    return not _op_in(left, right)


def _op_glob(left: Any, right: Any) -> bool:
    # treat left as string
    if left is None:
        return False
    return match_glob(str(left), str(right))


def _op_matches(left: Any, right: Any) -> bool:
    if left is None:
        return False
    return match_regex(str(left), str(right))


def _op_contains(left: Any, right: Any) -> bool:
    """
    For collections: right in left
    For strings: substring
    """
    if left is None:
        return False
    if isinstance(left, (list, tuple, set)):
        return right in left
    return str(right) in str(left)


_OPS: dict[str, Callable[[Any, Any], bool]] = {
    "==": _op_eq,
    "!=": _op_neq,
    "in": _op_in,
    "not_in": _op_not_in,
    "glob": _op_glob,
    "matches": _op_matches,
    "contains": _op_contains,
}

# Compiler


class RulesCompiler:
    """
    Compile RulesDocumentAst -> RuleSet (runtime compiled rules).

    Responsibilities:
    - Validate/normalize severity/action/target
    - Compile predicate expression trees to callables
    - Provide good compile-time errors with spans if available
    """

    def compile(self, doc: RulesDocumentAst) -> RuleSet:
        compiled: list[Rule] = []
        for r in doc.rules:
            compiled.append(self._compile_rule(r))
        return RuleSet(rules=tuple(compiled), metadata=dict(doc.metadata or {}))

    def _compile_rule(self, r: RuleAst) -> Rule:
        if r.when is None:
            raise self._err("Rule missing 'when' block", r)

        severity = self._compile_severity(r.severity, r)
        action = self._compile_action(r.action, r)
        target = self._compile_target(r.when, r)

        when = self._compile_when(r.when, target, r)

        except_preds: list[_CompiledWhen] = []
        for ex in r.except_when:
            # allow except_when to target the same space as the rule
            ex_target = self._compile_target(ex, r)
            if ex_target != target:
                raise self._err(
                    f"except_when target '{ex_target.value}' does not match rule target '{target.value}'",
                    r,
                )
            except_preds.append(self._compile_when(ex, target, r))

        # message fallback
        message = r.message or self._default_message(r, target)

        return Rule(
            id=r.id,
            name=r.name,
            description=r.description,
            severity=severity,
            action=action,
            target=target,
            when=when.predicate,
            except_when=tuple(x.predicate for x in except_preds),
            message=message,
            suggestion=r.suggestion,
            tags=tuple(r.tags),
            metadata=dict(r.metadata or {}),
            span=r.span,
        )

    def _compile_when(self, w: WhenAst, target: RuleTarget, r: RuleAst) -> _CompiledWhen:
        pred = self._compile_expr(w.predicate, target, r)
        return _CompiledWhen(target=target, predicate=pred)

    def _compile_expr(self, expr: ExprAst, target: RuleTarget, r: RuleAst) -> PredicateFn:
        if isinstance(expr, AndAst):
            items = [self._compile_expr(x, target, r) for x in expr.items]
            return lambda obj: all(p(obj) for p in items)

        if isinstance(expr, OrAst):
            items = [self._compile_expr(x, target, r) for x in expr.items]
            return lambda obj: any(p(obj) for p in items)

        if isinstance(expr, NotAst):
            if expr.item is None:
                raise self._err("NOT expression missing item", r)
            inner = self._compile_expr(expr.item, target, r)
            return lambda obj: not inner(obj)

        if isinstance(expr, CompareAst):
            if expr.left is None or expr.right is None:
                raise self._err("Compare expression requires left and right", r)

            left = expr.left
            op = expr.op
            right = expr.right

            if op not in _OPS:
                raise self._err(f"Unsupported operator: {op!r}", r)

            getter = self._compile_field_getter(left, target, r)
            rhs = _lit_value(right)
            op_fn = _OPS[op]

            return lambda obj: op_fn(getter(obj), rhs)

        raise self._err(f"Unsupported expression node: {type(expr).__name__}", r)

    def _compile_field_getter(self, field: FieldAst, target: RuleTarget, r: RuleAst) -> Callable[[object], Any]:
        path = (field.path or "").strip()
        if not path:
            raise self._err("Empty field reference", r)

        if target == RuleTarget.NODE:

            def getter(obj: object) -> Any:
                n = cast(IRNode, obj)
                try:
                    return _get_node_field(n, path)
                except KeyError as e:
                    raise self._err(str(e), r) from e

            return getter

        if target == RuleTarget.DEPENDENCY:

            def getter(obj: object) -> Any:
                e = cast(IREdge, obj)
                try:
                    return _get_edge_field(e, path)
                except KeyError as ex:
                    raise self._err(str(ex), r) from ex

            return getter

        raise self._err(f"Unknown rule target: {target}", r)

    # Enum compilation / validation

    def _compile_severity(self, s: str, r: RuleAst) -> Severity:
        val = (s or "").strip().lower()
        if val == "error":
            return Severity.ERROR
        if val == "warning":
            return Severity.WARNING
        if val == "info":
            return Severity.INFO
        raise self._err(f"Invalid severity: {s!r}", r)

    def _compile_action(self, a: str, r: RuleAst) -> RuleAction:
        val = (a or "").strip().lower()
        if val == "forbid":
            return RuleAction.FORBID
        if val == "allow":
            return RuleAction.ALLOW
        if val == "require":
            return RuleAction.REQUIRE
        raise self._err(f"Invalid action: {a!r}", r)

    def _compile_target(self, w: WhenAst, r: RuleAst) -> RuleTarget:
        t = (w.target or "").strip().lower()
        if t == "node":
            return RuleTarget.NODE
        if t == "dependency":
            return RuleTarget.DEPENDENCY
        raise self._err(f"Invalid target: {w.target!r}", r)

    def _default_message(self, r: RuleAst, target: RuleTarget) -> str:
        if target == RuleTarget.NODE:
            return f"Rule '{r.name}' matched a node that violates the architecture contract."
        return f"Rule '{r.name}' matched a dependency that violates the architecture contract."

    def _err(self, message: str, r: RuleAst) -> RulesCompileError:
        # Prefer span info if present
        span = r.span
        return RulesCompileError(
            message=message,
            file=None if span is None else span.file,
            line=None if span is None else span.line,
            column=None if span is None else span.column,
            details={"rule_id": r.id, "rule_name": r.name},
        )
