from pacta.reporting.types import RuleRef, Severity, Violation
from pacta.rules.explain import explain_rule, explain_violation
from pacta.rules.types import Rule, RuleAction, RuleTarget

# ============================================================
# Helpers
# ============================================================


def mk_rule_ref(rule_id: str, *, name: str | None = None, severity: Severity = Severity.ERROR) -> RuleRef:
    # Adjust if your RuleRef differs
    return RuleRef(id=rule_id, name=name or rule_id, severity=severity)


# ============================================================
# explain_violation
# ============================================================


def test_explain_violation_dependency_contains_key_info():
    v = Violation(
        rule=mk_rule_ref("r1", name="No domain -> infra"),
        message="Domain cannot depend on infra",
        context={
            "target": "dependency",
            "dep_type": "import",
            "src_fqname": "app.domain",
            "dst_fqname": "app.infra.db",
            "src_layer": "domain",
            "dst_layer": "infra",
        },
    )

    text = explain_violation(v)
    assert "Dependency violation" in text
    assert "import" in text
    assert "app.domain" in text
    assert "app.infra.db" in text
    assert "domain" in text
    assert "infra" in text


def test_explain_violation_dependency_falls_back_to_ids_if_fqname_missing():
    v = Violation(
        rule=mk_rule_ref("r1"),
        message="x",
        context={
            "target": "dependency",
            "dep_type": "import",
            "src_id": "python://repo::a",
            "dst_id": "python://repo::b",
        },
    )

    text = explain_violation(v)
    assert "python://repo::a" in text
    assert "python://repo::b" in text


def test_explain_violation_node_contains_kind_and_identity():
    v = Violation(
        rule=mk_rule_ref("r2"),
        message="No services in domain",
        context={
            "target": "node",
            "fqname": "app.domain.BillingService",
            "kind": "class",
            "layer": "domain",
            "context": "billing",
            "container": "billing",
        },
    )

    text = explain_violation(v)
    assert "Node violation" in text
    assert "class" in text
    assert "app.domain.BillingService" in text
    assert "layer=domain" in text
    assert "context=billing" in text
    assert "container=billing" in text


def test_explain_violation_unknown_target_falls_back_to_message():
    v = Violation(
        rule=mk_rule_ref("rX"),
        message="Something happened",
        context={},
    )

    assert explain_violation(v) == "Something happened"


# ============================================================
# explain_rule
# ============================================================


def test_explain_rule_dependency_forbid_format():
    rule = Rule(
        id="r1",
        name="No domain -> infra",
        description="Domain layer must not import infra layer.",
        severity=Severity.ERROR,
        action=RuleAction.FORBID,
        target=RuleTarget.DEPENDENCY,
        message="Domain cannot depend on infra",
    )

    text = explain_rule(rule)
    assert "[r1]" in text
    assert "No domain -> infra" in text
    assert "forbid dependencies" in text
    assert "(error)" in text
    assert "Domain layer must not import infra layer." in text


def test_explain_rule_node_require_format():
    rule = Rule(
        id="r2",
        name="Domain must exist",
        severity=Severity.WARNING,
        action=RuleAction.REQUIRE,
        target=RuleTarget.NODE,
        message="No domain layer detected",
    )

    text = explain_rule(rule)
    assert "[r2]" in text
    assert "require nodes" in text
    assert "(warning)" in text
