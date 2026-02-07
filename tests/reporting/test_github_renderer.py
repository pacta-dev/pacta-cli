from pacta import PACTA_VERSION
from pacta.reporting.renderers.github import GitHubReportRenderer
from pacta.reporting.types import (
    DiffSummary,
    Report,
    ReportLocation,
    RuleRef,
    RunInfo,
    Severity,
    Summary,
    TrendPoint,
    TrendSummary,
    Violation,
)


def _make_run(**overrides):
    defaults = dict(
        repo_root="/tmp/repo",
        commit="abc1234def",
        branch="feature/billing",
        model_file="architecture.yml",
        rules_files=("rules.pacta.yml",),
        baseline_ref="baseline",
        mode="full",
        created_at="2025-01-22T12:00:00+00:00",
        tool_version=PACTA_VERSION,
        metadata={},
    )
    defaults.update(overrides)
    return RunInfo(**defaults)


def _make_violation(
    *,
    rule_id="no-domain-infra",
    name="Domain cannot depend on Infra",
    severity=Severity.ERROR,
    status="new",
    file="src/domain/service.py",
    line=12,
    suggestion="Use dependency injection",
):
    return Violation(
        rule=RuleRef(id=rule_id, name=name, severity=severity),
        message="Forbidden dependency",
        status=status,
        location=ReportLocation(file=file, line=line, column=1),
        context={
            "target": "dependency",
            "dep_type": "import",
            "src_fqname": "app.domain.BillingService",
            "dst_fqname": "app.infra.PostgresClient",
            "src_layer": "domain",
            "dst_layer": "infra",
        },
        violation_key="key1",
        suggestion=suggestion,
    )


def _make_report(*, violations=(), diff=None, trends=None, baseline_ref="baseline"):
    all_v = list(violations)
    by_sev = {}
    by_status = {}
    by_rule = {}
    for v in all_v:
        sev = v.rule.severity.value
        by_sev[sev] = by_sev.get(sev, 0) + 1
        by_status[v.status] = by_status.get(v.status, 0) + 1
        by_rule[v.rule.id] = by_rule.get(v.rule.id, 0) + 1

    return Report(
        tool="pacta",
        version=PACTA_VERSION,
        run=_make_run(baseline_ref=baseline_ref),
        summary=Summary(
            total_violations=len(all_v),
            by_severity=by_sev,
            by_status=by_status,
            by_rule=by_rule,
            engine_errors=0,
        ),
        violations=tuple(all_v),
        engine_errors=(),
        diff=diff,
        trends=trends,
    )


class TestGitHubRendererHeader:
    def test_header_includes_branch_and_commit(self):
        report = _make_report()
        out = GitHubReportRenderer().render(report)
        assert "## Architecture Report" in out
        assert "`feature/billing`" in out
        assert "`abc1234`" in out
        assert "`baseline`" in out

    def test_no_branch_or_commit(self):
        report = Report(
            tool="pacta",
            version=PACTA_VERSION,
            run=_make_run(branch=None, commit=None, baseline_ref=None),
            summary=Summary(total_violations=0, by_severity={}, by_status={}, by_rule={}, engine_errors=0),
            violations=(),
            engine_errors=(),
        )
        out = GitHubReportRenderer().render(report)
        assert "## Architecture Report" in out
        assert "Branch" not in out


class TestGitHubRendererStructuralChanges:
    def test_diff_table_rendered(self):
        diff = DiffSummary(
            nodes_added=3,
            nodes_removed=1,
            edges_added=5,
            edges_removed=2,
            added_node_names=("app.billing.InvoiceService", "app.billing.TaxCalc"),
            removed_node_names=("app.legacy.OldBilling",),
        )
        report = _make_report(diff=diff)
        out = GitHubReportRenderer().render(report)
        assert "### Structural Changes" in out
        assert "+3" in out
        assert "-1" in out
        assert "`app.billing.InvoiceService`" in out
        assert "**Removed modules:**" in out

    def test_no_diff_section_when_empty(self):
        report = _make_report()
        out = GitHubReportRenderer().render(report)
        assert "### Structural Changes" not in out


class TestGitHubRendererViolations:
    def test_new_violations_with_baseline(self):
        v = _make_violation(status="new")
        report = _make_report(violations=[v], baseline_ref="baseline")
        out = GitHubReportRenderer().render(report)
        assert "### New Violations (action required)" in out
        assert "`no-domain-infra`" in out
        assert "src/domain/service.py:12" in out
        assert "Use dependency injection" in out

    def test_all_violations_shown_without_baseline(self):
        v = _make_violation(status="unknown")
        report = _make_report(violations=[v], baseline_ref=None)
        out = GitHubReportRenderer().render(report)
        assert "### Violation Details" in out
        assert "`no-domain-infra`" in out
        assert "src/domain/service.py:12" in out

    def test_severity_summary_without_baseline(self):
        v1 = _make_violation(status="unknown", severity=Severity.WARNING)
        v2 = _make_violation(status="unknown", severity=Severity.INFO, rule_id="other", name="Other")
        report = _make_report(violations=[v1, v2], baseline_ref=None)
        out = GitHubReportRenderer().render(report)
        assert "### Violations (2 total)" in out
        assert "Warning" in out
        assert "Info" in out

    def test_status_summary_with_baseline(self):
        new_v = _make_violation(status="new")
        existing_v = _make_violation(status="existing", rule_id="other-rule", name="Other")
        report = _make_report(violations=[new_v, existing_v], baseline_ref="baseline")
        out = GitHubReportRenderer().render(report)
        assert "### Violations Summary" in out
        assert "New" in out
        assert "Existing" in out

    def test_existing_violations_collapsible(self):
        v = _make_violation(status="existing")
        report = _make_report(violations=[v], baseline_ref="baseline")
        out = GitHubReportRenderer().render(report)
        assert "<details>" in out
        assert "Existing Violations" in out

    def test_fixed_violations_section(self):
        v = _make_violation(status="fixed", rule_id="no-circular", name="No circular deps")
        report = _make_report(violations=[v])
        out = GitHubReportRenderer().render(report)
        assert "### Fixed Violations" in out
        assert "~~`no-circular`" in out
        assert "(resolved)" in out

    def test_no_violations_no_summary(self):
        report = _make_report()
        out = GitHubReportRenderer().render(report)
        assert "### Violations" not in out


class TestGitHubRendererTrends:
    def test_trends_table_rendered(self):
        trends = TrendSummary(
            points=(
                TrendPoint(label="Jan 20", violations=5, nodes=40, edges=67, density=1.68),
                TrendPoint(label="Jan 22", violations=3, nodes=42, edges=67, density=1.60),
            ),
            violation_change=-2,
            node_change=2,
            edge_change=0,
            density_change=-0.08,
        )
        report = _make_report(trends=trends)
        out = GitHubReportRenderer().render(report)
        assert "### Architecture Trends (last 2 snapshots)" in out
        assert "Violations" in out
        assert "Improving" in out
        assert "-2" in out

    def test_no_trends_when_none(self):
        report = _make_report()
        out = GitHubReportRenderer().render(report)
        assert "### Architecture Trends" not in out


class TestGitHubRendererTableAlignment:
    def test_tables_have_aligned_columns(self):
        trends = TrendSummary(
            points=(TrendPoint(label="Jan 22", violations=3, nodes=42, edges=67, density=1.60),),
            violation_change=0,
            node_change=0,
            edge_change=0,
            density_change=0,
        )
        report = _make_report(trends=trends)
        out = GitHubReportRenderer().render(report)
        # All rows in a table should have the same length
        for line in out.split("\n"):
            if line.startswith("|") and "---" not in line:
                # Each cell should be padded
                assert "  " in line, f"Table row not padded: {line}"


class TestGitHubRendererFooter:
    def test_footer_includes_version(self):
        report = _make_report()
        out = GitHubReportRenderer().render(report)
        assert "Pacta" in out
        assert PACTA_VERSION in out


class TestGitHubRendererFullOutput:
    def test_full_report_with_baseline(self):
        diff = DiffSummary(
            nodes_added=3,
            nodes_removed=1,
            edges_added=5,
            edges_removed=2,
            added_node_names=("app.billing.InvoiceService",),
            removed_node_names=("app.legacy.OldBilling",),
        )
        trends = TrendSummary(
            points=(
                TrendPoint(label="Jan 20", violations=5, nodes=40, edges=67, density=1.68),
                TrendPoint(label="Jan 22", violations=3, nodes=42, edges=67, density=1.60),
            ),
            violation_change=-2,
            node_change=2,
            edge_change=0,
            density_change=-0.08,
        )
        new_v = _make_violation(status="new")
        fixed_v = _make_violation(status="fixed", rule_id="no-circular", name="No circular deps")

        report = _make_report(violations=[new_v, fixed_v], diff=diff, trends=trends)
        out = GitHubReportRenderer().render(report)

        assert "## Architecture Report" in out
        assert "### Structural Changes" in out
        assert "### Violations Summary" in out
        assert "### New Violations" in out
        assert "### Fixed Violations" in out
        assert "### Architecture Trends" in out
        assert "Generated by" in out

    def test_full_report_without_baseline(self):
        v1 = _make_violation(status="unknown", severity=Severity.WARNING)
        v2 = _make_violation(status="unknown", severity=Severity.INFO, rule_id="other", name="Other")
        report = _make_report(violations=[v1, v2], baseline_ref=None)
        out = GitHubReportRenderer().render(report)

        assert "## Architecture Report" in out
        assert "### Violations (2 total)" in out
        assert "### Violation Details" in out
        assert "`no-domain-infra`" in out
        assert "`other`" in out
        assert "Generated by" in out
        # No baseline-specific sections
        assert "### Violations Summary" not in out
        assert "### New Violations" not in out
