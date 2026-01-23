import pytest
from pacta.ir.types import (
    CanonicalId,
    DepType,
    IREdge,
    IRNode,
    Language,
    SymbolKind,
)
from pacta.rules.ast import (
    AndAst,
    CompareAst,
    DependencyWhenAst,
    FieldAst,
    LiteralAst,
    NodeWhenAst,
    NotAst,
    OrAst,
    RuleAst,
    RulesDocumentAst,
    SourceSpan,
)
from pacta.rules.compiler import RulesCompiler
from pacta.rules.errors import RulesCompileError
from pacta.rules.types import RuleAction, RuleTarget

# ============================================================
# Helpers
# ============================================================


def cid(fqname: str) -> CanonicalId:
    return CanonicalId(language=Language.PYTHON, code_root="repo", fqname=fqname)


def mk_node(
    fqname: str,
    *,
    kind: SymbolKind = SymbolKind.MODULE,
    path: str | None = None,
    name: str | None = None,
    container: str | None = None,
    layer: str | None = None,
    context: str | None = None,
    tags: tuple[str, ...] = (),
) -> IRNode:
    return IRNode(
        id=cid(fqname),
        kind=kind,
        name=name,
        path=path,
        loc=None,
        container=container,
        layer=layer,
        context=context,
        tags=tags,
        attributes={},
    )


def mk_edge(
    src: str,
    dst: str,
    *,
    dep_type: DepType = DepType.IMPORT,
    src_container: str | None = None,
    src_layer: str | None = None,
    src_context: str | None = None,
    dst_container: str | None = None,
    dst_layer: str | None = None,
    dst_context: str | None = None,
) -> IREdge:
    return IREdge(
        src=cid(src),
        dst=cid(dst),
        dep_type=dep_type,
        loc=None,
        confidence=1.0,
        details={},
        src_container=src_container,
        src_layer=src_layer,
        src_context=src_context,
        dst_container=dst_container,
        dst_layer=dst_layer,
        dst_context=dst_context,
    )


def doc_with(rule: RuleAst) -> RulesDocumentAst:
    return RulesDocumentAst(rules=(rule,), span=SourceSpan(file="rules.txt"))


def lit_str(s: str) -> LiteralAst:
    return LiteralAst(kind="string", value=s)


def lit_list(items: list[str]) -> LiteralAst:
    return LiteralAst(kind="list", value=items)


# ============================================================
# Tests
# ============================================================


def test_compile_dependency_rule_basic_eq_predicate():
    r = RuleAst(
        id="r1",
        name="No domain -> infra",
        severity="error",
        action="forbid",
        when=DependencyWhenAst(
            predicate=AndAst(
                items=(
                    CompareAst(left=FieldAst(path="from.layer"), op="==", right=lit_str("domain")),
                    CompareAst(left=FieldAst(path="to.layer"), op="==", right=lit_str("infra")),
                )
            )
        ),
        span=SourceSpan(file="rules.txt", line=1, column=1),
    )

    ruleset = RulesCompiler().compile(doc_with(r))
    assert len(ruleset.rules) == 1
    rule = ruleset.rules[0]

    assert rule.id == "r1"
    assert rule.target == RuleTarget.DEPENDENCY
    assert rule.action == RuleAction.FORBID

    e_ok = mk_edge("a", "b", src_layer="domain", dst_layer="infra")
    e_bad = mk_edge("a", "b", src_layer="domain", dst_layer="domain")

    assert rule.when(e_ok) is True
    assert rule.when(e_bad) is False


def test_compile_node_rule_glob_and_contains():
    r = RuleAst(
        id="r2",
        name="Domain services must be named *Service",
        severity="warning",
        action="forbid",
        when=NodeWhenAst(
            predicate=AndAst(
                items=(
                    CompareAst(left=FieldAst(path="layer"), op="==", right=lit_str("domain")),
                    CompareAst(left=FieldAst(path="name"), op="glob", right=lit_str("*Service")),
                    CompareAst(left=FieldAst(path="tags"), op="contains", right=lit_str("internal")),
                )
            )
        ),
    )

    rule = RulesCompiler().compile(doc_with(r)).rules[0]

    n1 = mk_node("x", layer="domain", name="BillingService", tags=("internal",))
    n2 = mk_node("x", layer="domain", name="Billing", tags=("internal",))
    n3 = mk_node("x", layer="infra", name="BillingService", tags=("internal",))

    assert rule.when(n1) is True
    assert rule.when(n2) is False
    assert rule.when(n3) is False


def test_compile_in_operator_with_list_literal():
    r = RuleAst(
        id="r3",
        name="Kind must be module or package",
        action="forbid",
        when=NodeWhenAst(
            predicate=CompareAst(
                left=FieldAst(path="kind"),
                op="in",
                right=lit_list(["module", "package"]),
            )
        ),
    )

    rule = RulesCompiler().compile(doc_with(r)).rules[0]

    n_mod = mk_node("a", kind=SymbolKind.MODULE)
    n_cls = mk_node("b", kind=SymbolKind.CLASS)

    assert rule.when(n_mod) is True
    assert rule.when(n_cls) is False


def test_compile_not_in_operator():
    r = RuleAst(
        id="r4",
        name="Not in infra",
        when=NodeWhenAst(
            predicate=CompareAst(
                left=FieldAst(path="layer"),
                op="not_in",
                right=lit_list(["infra"]),
            )
        ),
    )

    rule = RulesCompiler().compile(doc_with(r)).rules[0]
    assert rule.when(mk_node("a", layer="domain")) is True
    assert rule.when(mk_node("b", layer="infra")) is False


def test_invalid_severity_raises_compile_error():
    r = RuleAst(
        id="bad",
        name="Bad severity",
        severity="fatal",
        when=NodeWhenAst(predicate=LiteralAst(kind="bool", value=True)),
    )
    with pytest.raises(RulesCompileError) as ex:
        RulesCompiler().compile(doc_with(r))
    assert "Invalid severity" in str(ex.value)


def test_invalid_action_raises_compile_error():
    r = RuleAst(
        id="bad",
        name="Bad action",
        action="block",
        when=NodeWhenAst(predicate=LiteralAst(kind="bool", value=True)),
    )
    with pytest.raises(RulesCompileError) as ex:
        RulesCompiler().compile(doc_with(r))
    assert "Invalid action" in str(ex.value)


def test_invalid_operator_raises_compile_error():
    r = RuleAst(
        id="bad",
        name="Bad op",
        when=NodeWhenAst(
            predicate=CompareAst(
                left=FieldAst(path="layer"),
                op=">=",
                right=lit_str("domain"),
            )
        ),
    )
    with pytest.raises(RulesCompileError) as ex:
        RulesCompiler().compile(doc_with(r))
    assert "Unsupported operator" in str(ex.value)


def test_unknown_field_raises_compile_error_when_predicate_runs():
    r = RuleAst(
        id="bad",
        name="Bad field",
        when=NodeWhenAst(
            predicate=CompareAst(
                left=FieldAst(path="node.unknown_field"),
                op="==",
                right=lit_str("x"),
            )
        ),
        span=SourceSpan(file="rules.txt", line=10, column=5),
    )

    rule = RulesCompiler().compile(doc_with(r)).rules[0]

    with pytest.raises(RulesCompileError) as ex:
        rule.when(mk_node("a", layer="domain"))

    assert "Unknown node field" in str(ex.value) or "unknown node field" in str(ex.value).lower()
    assert ex.value.details is not None
    assert ex.value.details.get("rule_id") == "bad"


def test_except_when_target_mismatch_is_compile_error():
    r = RuleAst(
        id="r5",
        name="Mismatch except_when target",
        when=DependencyWhenAst(
            predicate=CompareAst(left=FieldAst(path="from.layer"), op="==", right=lit_str("domain"))
        ),
        except_when=(
            NodeWhenAst(predicate=CompareAst(left=FieldAst(path="layer"), op="==", right=lit_str("domain"))),
        ),
    )

    with pytest.raises(RulesCompileError) as ex:
        RulesCompiler().compile(doc_with(r))

    assert "except_when target" in str(ex.value)


def test_default_message_is_set_if_missing():
    r = RuleAst(
        id="r6",
        name="No explicit message",
        when=NodeWhenAst(predicate=CompareAst(left=FieldAst(path="layer"), op="==", right=lit_str("domain"))),
        message=None,
    )

    rule = RulesCompiler().compile(doc_with(r)).rules[0]
    assert isinstance(rule.message, str)
    assert "Rule" in rule.message


def test_not_or_and_expression_compilation():
    r = RuleAst(
        id="r7",
        name="Complex boolean logic",
        when=DependencyWhenAst(
            predicate=OrAst(
                items=(
                    CompareAst(left=FieldAst(path="dep.type"), op="==", right=lit_str("import")),
                    NotAst(item=CompareAst(left=FieldAst(path="to.layer"), op="==", right=lit_str("infra"))),
                )
            )
        ),
    )

    rule = RulesCompiler().compile(doc_with(r)).rules[0]

    e1 = mk_edge("a", "b", dep_type=DepType.IMPORT, dst_layer="infra")
    e2 = mk_edge("a", "b", dep_type=DepType.REQUIRE, dst_layer="domain")
    e3 = mk_edge("a", "b", dep_type=DepType.REQUIRE, dst_layer="infra")

    assert rule.when(e1) is True
    assert rule.when(e2) is True
    assert rule.when(e3) is False
