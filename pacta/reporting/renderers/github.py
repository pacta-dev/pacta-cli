from pacta.reporting.types import Report, Violation
from pacta.rules.explain import explain_violation


class GitHubReportRenderer:
    """
    Rich Markdown output for GitHub PR comments.

    Renders a descriptive architecture report including structural changes,
    violation details with suggestions, and architecture trends.
    """

    def __init__(self, *, max_detail_items: int = 10) -> None:
        self._max_items = max_detail_items

    def render(self, report: Report) -> str:
        lines: list[str] = []

        lines.append(self._render_header(report))
        lines.append(self._render_structural_changes(report))
        lines.append(self._render_violations_summary(report))
        lines.append(self._render_new_violations(report))
        lines.append(self._render_existing_violations(report))
        lines.append(self._render_fixed_violations(report))
        lines.append(self._render_trends(report))
        lines.append(self._render_footer(report))

        # Filter empty sections and join
        return "\n".join(s for s in lines if s) + "\n"

    def _render_header(self, report: Report) -> str:
        lines: list[str] = []

        lines.append("## Architecture Report")

        parts: list[str] = []
        if report.run.branch:
            parts.append(f"**Branch:** `{report.run.branch}`")
        if report.run.commit:
            short_commit = report.run.commit[:7]
            parts.append(f"**Commit:** `{short_commit}`")
        if report.run.baseline_ref:
            parts.append(f"**Baseline:** `{report.run.baseline_ref}`")

        if parts:
            lines.append(" | ".join(parts))
            lines.append("")

        return "\n".join(lines)

    def _render_structural_changes(self, report: Report) -> str:
        if report.diff is None:
            return ""

        d = report.diff
        if d.nodes_added == 0 and d.nodes_removed == 0 and d.edges_added == 0 and d.edges_removed == 0:
            return ""

        lines: list[str] = []
        lines.append("### Structural Changes")
        lines.append("")
        lines.append(
            _aligned_table(
                headers=["", "Added", "Removed"],
                rows=[
                    ["Modules/Classes", f"+{d.nodes_added}", f"-{d.nodes_removed}"],
                    ["Dependencies", f"+{d.edges_added}", f"-{d.edges_removed}"],
                ],
            )
        )
        lines.append("")

        if d.added_node_names:
            items = d.added_node_names[: self._max_items]
            names = ", ".join(f"`{n}`" for n in items)
            overflow = len(d.added_node_names) - self._max_items
            suffix = f" (+{overflow} more)" if overflow > 0 else ""
            lines.append(f"**New modules:** {names}{suffix}")

        if d.removed_node_names:
            items = d.removed_node_names[: self._max_items]
            names = ", ".join(f"`{n}`" for n in items)
            overflow = len(d.removed_node_names) - self._max_items
            suffix = f" (+{overflow} more)" if overflow > 0 else ""
            lines.append(f"**Removed modules:** {names}{suffix}")

        if d.added_edge_names:
            items = d.added_edge_names[: self._max_items]
            names = ", ".join(f"`{n}`" for n in items)
            overflow = len(d.added_edge_names) - self._max_items
            suffix = f" (+{overflow} more)" if overflow > 0 else ""
            lines.append(f"**New dependencies:** {names}{suffix}")

        if d.removed_edge_names:
            items = d.removed_edge_names[: self._max_items]
            names = ", ".join(f"`{n}`" for n in items)
            overflow = len(d.removed_edge_names) - self._max_items
            suffix = f" (+{overflow} more)" if overflow > 0 else ""
            lines.append(f"**Removed dependencies:** {names}{suffix}")

        if d.added_node_names or d.removed_node_names or d.added_edge_names or d.removed_edge_names:
            lines.append("")

        return "\n".join(lines)

    def _render_violations_summary(self, report: Report) -> str:
        s = report.summary
        if s.total_violations == 0:
            return ""

        has_baseline = report.run.baseline_ref is not None

        if has_baseline:
            # Show status-based summary (new/existing/fixed)
            rows: list[list[str]] = []
            for status in ("new", "existing", "fixed", "unknown"):
                count = s.by_status.get(status, 0)
                if count > 0:
                    label = {"new": "New", "existing": "Existing", "fixed": "Fixed", "unknown": "Unknown"}[status]
                    rows.append([label, str(count)])

            lines: list[str] = []
            lines.append("### Violations Summary")
            lines.append("")
            lines.append(_aligned_table(headers=["Status", "Count"], rows=rows))
        else:
            # No baseline: show severity-based summary
            rows = []
            for sev in ("error", "warning", "info"):
                count = s.by_severity.get(sev, 0)
                if count > 0:
                    rows.append([sev.capitalize(), str(count)])

            lines = []
            lines.append(f"### Violations ({s.total_violations} total)")
            lines.append("")
            lines.append(_aligned_table(headers=["Severity", "Count"], rows=rows))

        lines.append("")
        return "\n".join(lines)

    def _render_new_violations(self, report: Report) -> str:
        has_baseline = report.run.baseline_ref is not None

        if has_baseline:
            # With baseline: show only new violations
            target = [v for v in report.violations if v.status == "new"]
            if not target:
                return ""
            heading = "### New Violations (action required)"
        else:
            # Without baseline: show all violations
            target = list(report.violations)
            if not target:
                return ""
            heading = "### Violation Details"

        lines: list[str] = []
        lines.append(heading)
        lines.append("")

        for v in target:
            lines.extend(self._render_violation_block(v))
            lines.append("")

        return "\n".join(lines)

    def _render_existing_violations(self, report: Report) -> str:
        has_baseline = report.run.baseline_ref is not None
        if not has_baseline:
            return ""

        existing = [v for v in report.violations if v.status == "existing"]
        if not existing:
            return ""

        lines: list[str] = []
        lines.append(f"### Existing Violations ({len(existing)})")
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>Click to expand</summary>")
        lines.append("")

        for v in existing:
            lines.extend(self._render_violation_block(v))
            lines.append("")

        lines.append("</details>")
        lines.append("")
        return "\n".join(lines)

    def _render_fixed_violations(self, report: Report) -> str:
        fixed = [v for v in report.violations if v.status == "fixed"]
        if not fixed:
            return ""

        lines: list[str] = []
        lines.append("### Fixed Violations")
        lines.append("")

        for v in fixed:
            lines.append(f"- ~~`{v.rule.id}` — {v.rule.name}~~ (resolved)")

        lines.append("")
        return "\n".join(lines)

    def _render_violation_block(self, v: Violation) -> list[str]:
        lines: list[str] = []

        sev = v.rule.severity.value.upper() if hasattr(v.rule.severity, "value") else str(v.rule.severity).upper()

        lines.append(f"> **{sev}** `{v.rule.id}` — {v.rule.name}")

        loc = ""
        if v.location is not None:
            loc = f"`{v.location.file}:{v.location.line}`"

        explanation = explain_violation(v)
        if loc:
            lines.append(f"> {loc} — {explanation}")
        else:
            lines.append(f"> {explanation}")

        if v.suggestion:
            lines.append(f"> *{v.suggestion}*")

        return lines

    def _render_trends(self, report: Report) -> str:
        if report.trends is None or not report.trends.points:
            return ""

        t = report.trends
        last_point = t.points[-1]

        metrics = [
            ("Violations", last_point.violations, t.violation_change),
            ("Modules", last_point.nodes, t.node_change),
            ("Dependencies", last_point.edges, t.edge_change),
            ("Density", last_point.density, t.density_change),
        ]

        rows: list[list[str]] = []
        for name, current, change in metrics:
            trend = _trend_label(name, change)
            current_str = f"{current:.2f}" if name == "Density" else f"{current:.0f}"
            change_str = f"{change:+.2f}" if name == "Density" else f"{change:+.0f}"
            rows.append([name, trend, current_str, change_str])

        lines: list[str] = []
        lines.append(f"### Architecture Trends (last {len(t.points)} snapshots)")
        lines.append("")
        lines.append(
            _aligned_table(
                headers=["Metric", "Trend", "Current", "Change"],
                rows=rows,
            )
        )
        lines.append("")
        return "\n".join(lines)

    def _render_footer(self, report: Report) -> str:
        lines: list[str] = []
        lines.append("---")
        lines.append(f"*Generated by [Pacta](https://github.com/pacta-dev/pacta-cli) v{report.version}*")
        return "\n".join(lines)


def _trend_label(metric_name: str, change: float) -> str:
    if change < 0:
        direction = "Improving" if metric_name == "Violations" else "Decreasing"
        return f"↓ {direction}"
    elif change > 0:
        direction = "Worsening" if metric_name == "Violations" else "Growing"
        return f"↑ {direction}"
    else:
        return "→ Stable"


def _aligned_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a Markdown table with columns padded to equal width."""
    col_count = len(headers)
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < col_count:
                widths[i] = max(widths[i], len(cell))

    def _fmt_row(cells: list[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            parts.append(f" {cell:<{widths[i]}} ")
        return "|" + "|".join(parts) + "|"

    lines = [
        _fmt_row(headers),
        "|" + "|".join("-" * (w + 2) for w in widths) + "|",
    ]
    for row in rows:
        lines.append(_fmt_row(row))

    return "\n".join(lines)
