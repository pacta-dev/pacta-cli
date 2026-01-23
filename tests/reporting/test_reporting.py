from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

import pytest

# ----------------------------
# Utilities / fakes
# ----------------------------


class FakeSeverity(Enum):
    info = "info"
    warning = "warning"
    error = "error"


@dataclass(frozen=True, slots=True)
class ObjRule:
    id: str
    name: str
    severity: str | FakeSeverity = "error"
    description: str | None = None


@dataclass(frozen=True, slots=True)
class ObjLocation:
    file: str
    line: int
    column: int = 1
    end_line: int | None = None
    end_column: int | None = None


@dataclass(frozen=True, slots=True)
class ObjViolation:
    rule: ObjRule
    message: str
    status: str = "unknown"
    location: ObjLocation | None = None
    context: Mapping[str, Any] = ()
    violation_key: str | None = None
    suggestion: str | None = None


@dataclass(frozen=True, slots=True)
class ObjEngineError:
    type: str
    message: str
    location: ObjLocation | None = None
    details: Mapping[str, Any] = ()


@dataclass(frozen=True, slots=True)
class ObjDiff:
    nodes_added: int
    nodes_removed: int
    edges_added: int
    edges_removed: int


# ----------------------------
# Fixtures
# ----------------------------


@pytest.fixture(autouse=True)
def patch_builder_severity(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    reporting.builder imports Severity from pacta.ir.types at import time.
    If your Severity enum differs, this patch makes tests stable and isolated.
    """
    import pacta.reporting.builder as rb

    monkeypatch.setattr(rb, "Severity", FakeSeverity, raising=True)


@pytest.fixture
def runinfo(tmp_path):
    from pacta.reporting.types import RunInfo

    return RunInfo(
        repo_root=str(tmp_path),
        commit="abc123",
        branch="main",
        model_file="architecture.yaml",
        rules_files=("pacta.rules",),
        baseline_ref="baseline",
        mode="full",
        created_at=None,
        tool_version="0.1.0-test",
        metadata={"x": 1},
    )


# ----------------------------
# Tests: DefaultReportBuilder normalization
# ----------------------------


def test_builder_fills_created_at_and_merges_metadata(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder

    b = DefaultReportBuilder(tool="pacta", version="0.1.0")
    report = b.build(run=runinfo, metadata={"y": 2})

    assert report.tool == "pacta"
    assert report.version == "0.1.0"
    assert report.run.created_at is not None
    assert report.run.metadata["x"] == 1
    assert report.run.metadata["y"] == 2


def test_builder_accepts_violation_objects_and_dicts(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder
    from pacta.reporting.types import ReportLocation, RuleRef, Violation

    # already-normalized object
    v1 = Violation(
        rule=RuleRef(id="r1", name="R1", severity=FakeSeverity.error, description=None),
        message="m1",
        status="new",
        location=ReportLocation(file="a.py", line=1, column=1),
        context={"b": 2},
        violation_key="k1",
        suggestion=None,
    )

    # dict-like violation with dict-like rule
    v2 = {
        "rule": {"id": "r2", "name": "R2", "severity": "warning", "description": "d"},
        "message": "m2",
        "status": "existing",
        "location": {"file": "b.py", "line": 2, "column": 5},
        "context": {"a": 1},
        "violation_key": "k2",
        "suggestion": "do x",
    }

    report = DefaultReportBuilder(tool="pacta", version="0.1.0").build(
        run=runinfo,
        violations=[v2, v1],
    )

    assert len(report.violations) == 2

    # normalized rule severity becomes enum (FakeSeverity)
    sev_values = {vv.rule.id: vv.rule.severity.value for vv in report.violations}
    assert sev_values["r1"] == "error"
    assert sev_values["r2"] == "warning"


def test_builder_raises_if_violation_missing_rule(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder

    with pytest.raises(TypeError):
        DefaultReportBuilder().build(run=runinfo, violations=[{"message": "oops"}])


def test_builder_normalizes_engine_errors_from_dict_and_object(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder

    e1 = {"type": "parse_error", "message": "bad rules", "location": {"file": "pacta.rules", "line": 1, "column": 1}}
    e2 = ObjEngineError(
        type="runtime_error", message="boom", location=ObjLocation(file="x.py", line=9), details={"z": 7}
    )

    report = DefaultReportBuilder().build(run=runinfo, engine_errors=[e2, e1])
    assert len(report.engine_errors) == 2
    assert {e.type for e in report.engine_errors} == {"parse_error", "runtime_error"}


def test_builder_normalizes_diff_snake_and_camel_case(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder

    diff1 = {"nodes_added": 1, "nodes_removed": 2, "edges_added": 3, "edges_removed": 4}
    diff2 = {"nodesAdded": 5, "nodesRemoved": 6, "edgesAdded": 7, "edgesRemoved": 8}

    r1 = DefaultReportBuilder().build(run=runinfo, diff=diff1)
    r2 = DefaultReportBuilder().build(run=runinfo, diff=diff2)

    assert (r1.diff.nodes_added, r1.diff.nodes_removed, r1.diff.edges_added, r1.diff.edges_removed) == (1, 2, 3, 4)
    assert (r2.diff.nodes_added, r2.diff.nodes_removed, r2.diff.edges_added, r2.diff.edges_removed) == (5, 6, 7, 8)


def test_builder_summary_counts(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder

    violations = [
        {"rule": {"id": "r1", "name": "R1", "severity": "error"}, "message": "m1", "status": "new"},
        {"rule": {"id": "r1", "name": "R1", "severity": "error"}, "message": "m2", "status": "existing"},
        {"rule": {"id": "r2", "name": "R2", "severity": "warning"}, "message": "m3", "status": "unknown"},
    ]
    errors = [
        {"type": "runtime_error", "message": "boom"},
        {"type": "parse_error", "message": "bad"},
    ]

    report = DefaultReportBuilder().build(run=runinfo, violations=violations, engine_errors=errors)

    s = report.summary
    assert s.total_violations == 3
    assert s.engine_errors == 2
    assert s.by_rule["r1"] == 2
    assert s.by_rule["r2"] == 1
    assert s.by_severity["error"] == 2
    assert s.by_severity["warning"] == 1
    assert s.by_status["new"] == 1
    assert s.by_status["existing"] == 1
    assert s.by_status["unknown"] == 1


def test_builder_sorting_is_deterministic(runinfo):
    """
    Ensures builder sorts violations deterministically, so renderers do not need to sort.
    """
    from pacta.reporting.builder import DefaultReportBuilder

    v_a = {
        "rule": {"id": "r2", "name": "R2", "severity": "warning"},
        "message": "m",
        "status": "new",
        "location": {"file": "b.py", "line": 2, "column": 1},
        "violation_key": "2",
    }
    v_b = {
        "rule": {"id": "r1", "name": "R1", "severity": "error"},
        "message": "m",
        "status": "new",
        "location": {"file": "a.py", "line": 1, "column": 1},
        "violation_key": "1",
    }
    v_c = {
        "rule": {"id": "r1", "name": "R1", "severity": "error"},
        "message": "m",
        "status": "existing",
        "location": {"file": "a.py", "line": 1, "column": 1},
        "violation_key": "3",
    }

    report = DefaultReportBuilder().build(run=runinfo, violations=[v_a, v_c, v_b])

    # error before warning; within error r1; within r1 status existing vs new is deterministic
    ids = [(v.rule.id, v.status, v.location.file if v.location else "") for v in report.violations]
    assert ids[0][0] == "r1"
    assert ids[-1][0] == "r2"


# ----------------------------
# Tests: JsonReportRenderer
# ----------------------------


def test_json_renderer_is_deterministic_and_newline_terminated(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder
    from pacta.reporting.renderers.json import JsonReportRenderer

    violations = [
        {
            "rule": {"id": "r1", "name": "R1", "severity": "error"},
            "message": "m1",
            "status": "new",
            "context": {"b": 2, "a": 1},
        },  # intentionally unsorted keys
    ]

    report = DefaultReportBuilder(tool="pacta", version="0.1.0").build(run=runinfo, violations=violations)
    renderer = JsonReportRenderer()

    out1 = renderer.render(report)
    out2 = renderer.render(report)

    assert out1.endswith("\n")
    assert out1 == out2

    # JSON parseable
    data = __import__("json").loads(out1)
    assert data["tool"] == "pacta"
    assert data["summary"]["total_violations"] == 1

    # context keys deterministic in JSON (sorted by our json util)
    ctx = data["violations"][0]["context"]
    assert list(ctx.keys()) == ["a", "b"]


# ----------------------------
# Tests: TextReportRenderer
# ----------------------------


def test_text_renderer_no_violations(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder
    from pacta.reporting.renderers.text import TextReportRenderer

    report = DefaultReportBuilder(tool="pacta", version="0.1.0").build(run=runinfo)
    text = TextReportRenderer(verbosity="verbose").render(report)

    assert "No violations found." in text
    assert "Summary:" in text
    assert "violations: 0" in text


def test_text_renderer_renders_diff_and_baseline(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder
    from pacta.reporting.renderers.text import TextReportRenderer

    report = DefaultReportBuilder(tool="pacta", version="0.1.0").build(
        run=runinfo,
        diff={"nodes_added": 1, "nodes_removed": 2, "edges_added": 3, "edges_removed": 4},
    )
    text = TextReportRenderer(verbosity="verbose").render(report)

    assert "baseline: baseline" in text
    assert "Diff:" in text
    assert "nodes: +1  -2" in text
    assert "edges: +3  -4" in text


def test_text_renderer_renders_engine_errors_and_context_sorted(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder
    from pacta.reporting.renderers.text import TextReportRenderer

    violations = [
        {
            "rule": {"id": "r1", "name": "R1", "severity": "error"},
            "message": "Domain depends on Infra",
            "status": "new",
            "location": {"file": "x.py", "line": 10, "column": 3},
            "context": {"to": "infra", "from": "domain"},  # intentionally unsorted keys
            "violation_key": "vk",
            "suggestion": "move import",
        }
    ]
    errors = [
        {
            "type": "parse_error",
            "message": "bad rules",
            "location": {"file": "pacta.rules", "line": 1, "column": 1},
            "details": {"b": 2, "a": 1},
        },
    ]

    report = DefaultReportBuilder(tool="pacta", version="0.1.0").build(
        run=runinfo,
        violations=violations,
        engine_errors=errors,
    )

    text = TextReportRenderer(verbosity="verbose").render(report)

    assert "Engine Errors:" in text
    assert "parse_error" in text
    assert "bad rules" in text
    # details sorted
    assert "a: 1" in text
    assert "b: 2" in text

    assert "Violations:" in text
    assert "[r1]" in text
    assert "status: new" in text
    assert "key: vk" in text
    assert "suggestion: move import" in text

    # context sorted: 'from' before 'to'
    idx_from = text.find("from:")
    idx_to = text.find("to:")
    assert idx_from != -1 and idx_to != -1
    assert idx_from < idx_to


# ----------------------------
# Tests: TextReportRenderer verbosity levels
# ----------------------------


def test_text_renderer_quiet_no_violations(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder
    from pacta.reporting.renderers.text import TextReportRenderer

    report = DefaultReportBuilder(tool="pacta", version="0.1.0").build(run=runinfo)
    text = TextReportRenderer(verbosity="quiet").render(report)

    assert text == "✓ No violations\n"


def test_text_renderer_quiet_with_violations(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder
    from pacta.reporting.renderers.text import TextReportRenderer

    violations = [
        {"rule": {"id": "r1", "name": "R1", "severity": "error"}, "message": "m1", "status": "new"},
        {"rule": {"id": "r2", "name": "R2", "severity": "warning"}, "message": "m2", "status": "baseline"},
    ]
    report = DefaultReportBuilder(tool="pacta", version="0.1.0").build(run=runinfo, violations=violations)
    text = TextReportRenderer(verbosity="quiet").render(report)

    assert "2 violations" in text
    assert "1 error" in text
    assert "1 warning" in text
    # Status summary
    assert "1 baseline" in text
    assert "1 new" in text
    # Should NOT contain violation details
    assert "[r1]" not in text
    assert "m1" not in text


def test_text_renderer_normal_default(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder
    from pacta.reporting.renderers.text import TextReportRenderer

    violations = [
        {
            "rule": {"id": "r1", "name": "R1", "severity": "error"},
            "message": "Domain depends on Infra",
            "status": "new",
            "context": {"to": "infra", "from": "domain"},
            "violation_key": "vk",
            "suggestion": "move import",
        }
    ]
    report = DefaultReportBuilder(tool="pacta", version="0.1.0").build(run=runinfo, violations=violations)
    text = TextReportRenderer(verbosity="normal").render(report)

    # Should contain summary and violation header/message
    assert "1 violations" in text
    assert "[r1]" in text
    assert "Domain depends on Infra" in text

    # Status and suggestion shown in normal mode
    assert "status: new" in text
    assert "suggestion: move import" in text

    # Should NOT contain verbose-only details
    assert "Summary:" not in text  # verbose header
    assert "key: vk" not in text  # key only in verbose
    assert "from:" not in text  # context only in verbose


def test_text_renderer_normal_no_violations(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder
    from pacta.reporting.renderers.text import TextReportRenderer

    report = DefaultReportBuilder(tool="pacta", version="0.1.0").build(run=runinfo)
    text = TextReportRenderer(verbosity="normal").render(report)

    assert "✓ No violations" in text


# ----------------------------
# Edge-cases: normalization of partial locations
# ----------------------------


def test_builder_location_defaults_column_to_1(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder

    v = {
        "rule": {"id": "r1", "name": "R1", "severity": "error"},
        "message": "m",
        "status": "new",
        "location": {"file": "a.py", "line": 5},  # no column
    }
    report = DefaultReportBuilder().build(run=runinfo, violations=[v])
    loc = report.violations[0].location
    assert loc is not None
    assert loc.column == 1


def test_builder_engine_error_location_defaults_column_to_1(runinfo):
    from pacta.reporting.builder import DefaultReportBuilder

    e = {"type": "runtime_error", "message": "boom", "location": {"file": "a.py", "line": 5}}
    report = DefaultReportBuilder().build(run=runinfo, engine_errors=[e])
    loc = report.engine_errors[0].location
    assert loc is not None
    assert loc.column == 1
