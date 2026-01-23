import dataclasses

import pytest
from pacta.rules.ast import (
    AndAst,
    CompareAst,
    DependencyWhenAst,
    ExprAst,
    FieldAst,
    LiteralAst,
    NodeWhenAst,
    NotAst,
    OrAst,
    RuleAst,
    RulesDocumentAst,
    SourceSpan,
)


def test_sourcespan_defaults():
    s = SourceSpan()
    assert s.file is None
    assert s.line is None
    assert s.column is None
    assert s.end_line is None
    assert s.end_column is None


def test_rules_document_defaults_are_safe():
    doc = RulesDocumentAst()
    assert doc.rules == ()
    assert doc.span is None
    assert isinstance(doc.metadata, dict)
    assert doc.metadata == {}


def test_rule_ast_defaults():
    r = RuleAst(id="r1", name="Rule 1")
    assert r.description is None
    assert r.severity == "error"
    assert r.action == "forbid"
    assert r.when is None
    assert r.except_when == ()
    assert r.message is None
    assert r.suggestion is None
    assert r.tags == ()
    assert r.span is None
    assert isinstance(r.metadata, dict)


def test_dependency_when_ast_forces_target():
    w = DependencyWhenAst(predicate=LiteralAst(kind="bool", value=True))
    assert w.target == "dependency"
    assert isinstance(w.predicate, ExprAst)
    assert w.span is None


def test_node_when_ast_forces_target():
    w = NodeWhenAst(predicate=LiteralAst(kind="bool", value=True))
    assert w.target == "node"
    assert isinstance(w.predicate, ExprAst)
    assert w.span is None


def test_and_or_not_compare_shapes():
    expr = AndAst(
        items=(
            CompareAst(
                left=FieldAst(path="from.layer"),
                op="==",
                right=LiteralAst(kind="string", value="domain"),
            ),
            NotAst(
                item=CompareAst(
                    left=FieldAst(path="to.layer"),
                    op="==",
                    right=LiteralAst(kind="string", value="infra"),
                )
            ),
        )
    )
    assert isinstance(expr, ExprAst)
    assert isinstance(expr, AndAst)
    assert len(expr.items) == 2

    or_expr = OrAst(items=(expr,))
    assert isinstance(or_expr, OrAst)
    assert or_expr.items[0] is expr

    not_expr = NotAst(item=or_expr)
    assert isinstance(not_expr, NotAst)
    assert not_expr.item is or_expr


def test_compare_ast_defaults():
    c = CompareAst()
    assert c.left is None
    assert c.right is None
    assert c.op == "=="


def test_field_ast_defaults():
    f = FieldAst()
    assert f.path == ""


def test_literal_ast_defaults():
    l = LiteralAst()  # noqa: E741
    assert l.kind == "string"
    assert l.value is None


def test_rule_document_roundtrip_construction():
    rule = RuleAst(
        id="no-domain-to-infra",
        name="Domain must not depend on infra",
        when=DependencyWhenAst(
            predicate=CompareAst(
                left=FieldAst(path="from.layer"),
                op="==",
                right=LiteralAst(kind="string", value="domain"),
            )
        ),
        tags=("layers", "ddd"),
        span=SourceSpan(file="rules.txt", line=1, column=1),
        metadata={"x": 1},
    )
    doc = RulesDocumentAst(rules=(rule,), span=SourceSpan(file="rules.txt"))

    assert doc.rules[0].id == "no-domain-to-infra"
    assert doc.rules[0].when is not None
    assert doc.rules[0].when.target == "dependency"
    assert doc.span is not None
    assert doc.span.file == "rules.txt"


def test_ast_dataclasses_are_frozen():
    rule = RuleAst(id="r1", name="Rule 1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        # type: ignore[attr-defined]
        rule.name = "Mutated"


def test_when_ast_is_frozen():
    w = NodeWhenAst(predicate=LiteralAst(kind="bool", value=True))
    with pytest.raises(dataclasses.FrozenInstanceError):
        # type: ignore[attr-defined]
        w.target = "dependency"
