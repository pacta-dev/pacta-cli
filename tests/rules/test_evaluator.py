from pacta.ir.index import build_index
from pacta.ir.types import (
    ArchitectureIR,
    CanonicalId,
    DepType,
    IREdge,
    IRNode,
    Language,
    SymbolKind,
)
from pacta.reporting.types import Violation
from pacta.rules.ast import (
    AndAst,
    CompareAst,
    DependencyWhenAst,
    FieldAst,
    LiteralAst,
    NodeWhenAst,
    RuleAst,
    RulesDocumentAst,
)
from pacta.rules.compiler import RulesCompiler
from pacta.rules.evaluator import DefaultRuleEvaluator

# Helpers


def cid(fqname: str) -> CanonicalId:
    return CanonicalId(language=Language.PYTHON, code_root="repo", fqname=fqname)


def mk_node(
    fqname: str,
    *,
    kind: SymbolKind = SymbolKind.MODULE,
    name: str | None = None,
    path: str | None = None,
    layer: str | None = None,
    context: str | None = None,
    container: str | None = None,
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
    src_layer: str | None = None,
    dst_layer: str | None = None,
    src_context: str | None = None,
    dst_context: str | None = None,
    src_container: str | None = None,
    dst_container: str | None = None,
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


def mk_ir(nodes: list[IRNode], edges: list[IREdge]) -> ArchitectureIR:
    return ArchitectureIR(
        schema_version=1,
        produced_by="tests",
        repo_root="repo",
        nodes=tuple(nodes),
        edges=tuple(edges),
        metadata={},
    )


def lit_str(s: str) -> LiteralAst:
    return LiteralAst(kind="string", value=s)


def compile_rules(*rules: RuleAst):
    doc = RulesDocumentAst(rules=tuple(rules))
    return RulesCompiler().compile(doc)


# Tests


def test_forbid_dependency_rule_emits_violation_per_matching_edge():
    ruleset = compile_rules(
        RuleAst(
            id="no-domain-to-infra",
            name="Domain must not depend on Infra",
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
            message="Domain cannot depend on infra",
        )
    )

    ir = mk_ir(
        nodes=[
            mk_node("app.domain", layer="domain"),
            mk_node("app.infra", layer="infra"),
            mk_node("app.other", layer="domain"),
        ],
        edges=[
            mk_edge("app.domain", "app.infra", src_layer="domain", dst_layer="infra", dep_type=DepType.IMPORT),
            mk_edge("app.other", "app.domain", src_layer="domain", dst_layer="domain", dep_type=DepType.IMPORT),
        ],
    )

    violations = DefaultRuleEvaluator().evaluate(ir, ruleset)
    assert isinstance(violations, tuple)
    assert len(violations) == 1

    v = violations[0]
    assert isinstance(v, Violation)

    # RuleRef is attached
    assert v.rule.id == "no-domain-to-infra"
    assert v.rule.name == "Domain must not depend on Infra"

    # Payload is in context
    assert v.message == "Domain cannot depend on infra"
    assert v.context["target"] == "dependency"
    assert v.context["dep_type"] == DepType.IMPORT.value
    assert v.context["src_id"] == str(ir.edges[0].src)
    assert v.context["dst_id"] == str(ir.edges[0].dst)
    assert v.context["src_fqname"] == ir.edges[0].src.fqname
    assert v.context["dst_fqname"] == ir.edges[0].dst.fqname


def test_forbid_node_rule_emits_violation_per_matching_node():
    ruleset = compile_rules(
        RuleAst(
            id="no-domain-services",
            name="No services in domain layer",
            severity="warning",
            action="forbid",
            when=NodeWhenAst(
                predicate=AndAst(
                    items=(
                        CompareAst(left=FieldAst(path="layer"), op="==", right=lit_str("domain")),
                        CompareAst(left=FieldAst(path="name"), op="glob", right=lit_str("*Service")),
                    )
                )
            ),
            message="Service classes are not allowed in domain layer",
        )
    )

    n1 = mk_node("app.domain.BillingService", kind=SymbolKind.CLASS, layer="domain", name="BillingService")
    n2 = mk_node("app.domain.Invoice", kind=SymbolKind.CLASS, layer="domain", name="Invoice")
    n3 = mk_node("app.infra.EmailService", kind=SymbolKind.CLASS, layer="infra", name="EmailService")

    ir = mk_ir(nodes=[n1, n2, n3], edges=[])

    violations = DefaultRuleEvaluator().evaluate(ir, ruleset)
    assert len(violations) == 1

    v = violations[0]
    assert v.rule.id == "no-domain-services"
    assert v.context["target"] == "node"
    assert v.context["node_id"] == str(n1.id)
    assert v.context["fqname"] == n1.id.fqname
    assert v.context["kind"] == n1.kind.value


def test_except_when_excludes_matches():
    ruleset = compile_rules(
        RuleAst(
            id="no-domain-to-infra-except-allowed",
            name="Domain must not depend on infra (except allowed)",
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
            except_when=(
                DependencyWhenAst(
                    predicate=CompareAst(
                        left=FieldAst(path="to.fqname"),
                        op="glob",
                        right=lit_str("app.infra.allowed.*"),
                    )
                ),
            ),
            message="Domain cannot depend on infra (except allowed)",
        )
    )

    e_allowed = mk_edge(
        "app.domain",
        "app.infra.allowed.db",
        src_layer="domain",
        dst_layer="infra",
        dep_type=DepType.IMPORT,
    )
    e_bad = mk_edge(
        "app.domain",
        "app.infra.forbidden",
        src_layer="domain",
        dst_layer="infra",
        dep_type=DepType.IMPORT,
    )

    ir = mk_ir(
        nodes=[
            mk_node("app.domain", layer="domain"),
            mk_node("app.infra.allowed.db", layer="infra"),
            mk_node("app.infra.forbidden", layer="infra"),
        ],
        edges=[e_allowed, e_bad],
    )

    violations = DefaultRuleEvaluator().evaluate(ir, ruleset)
    assert len(violations) == 1
    assert violations[0].context["dst_fqname"] == "app.infra.forbidden"


def test_require_rule_emits_single_violation_if_no_match():
    ruleset = compile_rules(
        RuleAst(
            id="require-domain-layer",
            name="Domain layer must exist",
            severity="error",
            action="require",
            when=NodeWhenAst(
                predicate=CompareAst(
                    left=FieldAst(path="layer"),
                    op="==",
                    right=lit_str("domain"),
                )
            ),
            message="No domain layer detected",
        )
    )

    ir = mk_ir(
        nodes=[mk_node("app.infra", layer="infra")],
        edges=[],
    )

    violations = DefaultRuleEvaluator().evaluate(ir, ruleset)
    assert len(violations) == 1

    v = violations[0]
    assert v.rule.id == "require-domain-layer"
    assert v.message == "No domain layer detected"
    assert v.context["action"] == "require"
    assert v.context["target"] == "node"
    assert v.location is None


def test_evaluator_accepts_irindex_input_equivalently():
    ruleset = compile_rules(
        RuleAst(
            id="no-domain-to-infra",
            name="Domain must not depend on Infra",
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
            message="Domain cannot depend on infra",
        )
    )

    ir = mk_ir(
        nodes=[
            mk_node("app.domain", layer="domain"),
            mk_node("app.infra", layer="infra"),
        ],
        edges=[
            mk_edge("app.domain", "app.infra", src_layer="domain", dst_layer="infra"),
        ],
    )

    idx = build_index(ir)

    v1 = DefaultRuleEvaluator().evaluate(ir, ruleset)
    v2 = DefaultRuleEvaluator().evaluate(idx, ruleset)

    assert len(v1) == len(v2) == 1
    assert v1[0].rule.id == v2[0].rule.id
    assert v1[0].context["src_fqname"] == v2[0].context["src_fqname"]
    assert v1[0].context["dst_fqname"] == v2[0].context["dst_fqname"]
