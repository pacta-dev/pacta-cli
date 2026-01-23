from dataclasses import replace

from pacta.reporting.types import RuleRef, Severity, Violation
from pacta.rules.baseline import BaselineComparer, ViolationKeyStrategy

# Helpers


def mk_rule(rule_id: str, *, name: str | None = None, severity: Severity = Severity.ERROR) -> RuleRef:
    # Adjust fields here if your RuleRef differs.
    return RuleRef(
        id=rule_id,
        name=name or rule_id,
        severity=severity,
    )


def v_node(rule_id: str, node_id: str, *, msg: str = "node violation") -> Violation:
    return Violation(
        rule=mk_rule(rule_id),
        message=msg,
        context={
            "target": "node",
            "node_id": node_id,
            "fqname": node_id,
            "kind": "module",
        },
    )


def v_dep(
    rule_id: str,
    src_id: str,
    dst_id: str,
    *,
    dep_type: str = "import",
    msg: str = "dep violation",
) -> Violation:
    return Violation(
        rule=mk_rule(rule_id),
        message=msg,
        context={
            "target": "dependency",
            "dep_type": dep_type,
            "src_id": src_id,
            "dst_id": dst_id,
            "src_fqname": src_id,
            "dst_fqname": dst_id,
        },
    )


# Tests: key strategy


def test_key_for_node_depends_on_rule_and_node_id():
    ks = ViolationKeyStrategy()

    a1 = v_node("r1", "python://repo::a")
    a2 = v_node("r1", "python://repo::a")
    b1 = v_node("r1", "python://repo::b")
    a_other_rule = v_node("r2", "python://repo::a")

    assert ks.key_for(a1) == ks.key_for(a2)
    assert ks.key_for(a1) != ks.key_for(b1)
    assert ks.key_for(a1) != ks.key_for(a_other_rule)


def test_key_for_dependency_depends_on_rule_dep_type_src_dst():
    ks = ViolationKeyStrategy()

    e1 = v_dep("r1", "A", "B", dep_type="import")
    e2 = v_dep("r1", "A", "B", dep_type="import")
    e3 = v_dep("r1", "A", "C", dep_type="import")
    e4 = v_dep("r1", "A", "B", dep_type="require")
    e5 = v_dep("r2", "A", "B", dep_type="import")

    assert ks.key_for(e1) == ks.key_for(e2)
    assert ks.key_for(e1) != ks.key_for(e3)
    assert ks.key_for(e1) != ks.key_for(e4)
    assert ks.key_for(e1) != ks.key_for(e5)


def test_key_is_independent_of_message_and_extra_context_noise():
    ks = ViolationKeyStrategy()

    v1 = v_dep("r1", "A", "B", dep_type="import", msg="x")
    v2 = v_dep("r1", "A", "B", dep_type="import", msg="y")

    # extra noise fields in context should not affect default key
    v2 = replace(v2, context={**v2.context, "src_layer": "domain", "dst_layer": "infra"})

    assert ks.key_for(v1) == ks.key_for(v2)


def test_key_unknown_target_falls_back_to_rule_and_message():
    ks = ViolationKeyStrategy()

    v1 = Violation(rule=mk_rule("rX"), message="something", context={})
    v2 = Violation(rule=mk_rule("rX"), message="something else", context={})

    assert ks.key_for(v1) != ks.key_for(v2)


# Tests: BaselineComparer


def test_compare_classifies_new_existing_fixed():
    comparer = BaselineComparer()

    baseline = [
        v_dep("r1", "A", "B"),
        v_node("r2", "X"),
    ]
    current = [
        v_dep("r1", "A", "B"),  # existing
        v_dep("r1", "A", "C"),  # new
    ]

    res = comparer.compare(current=current, baseline=baseline)

    assert len(res.existing) == 1
    assert len(res.new) == 1
    assert len(res.fixed) == 1

    assert res.existing[0].context["dst_id"] == "B"
    assert res.new[0].context["dst_id"] == "C"
    assert res.fixed[0].context["target"] == "node"


def test_compare_is_deterministic_sorted_by_key():
    comparer = BaselineComparer()

    current = [
        v_dep("r1", "A", "C"),
        v_dep("r1", "A", "B"),
        v_node("r2", "X"),
    ]
    baseline = [
        v_dep("r1", "A", "B"),
        v_node("r2", "X"),
        v_dep("r1", "A", "C"),
    ]

    res = comparer.compare(current=current, baseline=baseline)

    assert res.new == ()
    assert res.fixed == ()
    assert len(res.existing) == 3

    keys = [comparer.key_strategy.key_for(v) for v in res.existing]
    assert keys == sorted(keys)


def test_compare_handles_duplicates_in_inputs_last_wins_in_map():
    comparer = BaselineComparer()
    ks = comparer.key_strategy

    v1 = v_dep("r1", "A", "B", msg="first")
    v2 = v_dep("r1", "A", "B", msg="second")  # same identity

    assert ks.key_for(v1) == ks.key_for(v2)

    res = comparer.compare(current=[v1, v2], baseline=[])

    assert len(res.new) == 1
    assert res.new[0].message == "second"
