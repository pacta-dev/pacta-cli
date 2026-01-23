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
# SPDX-License-Identifier: AGPL-3.0-only

from typing import Literal

from pacta.reporting.types import EngineError, Report, Violation

Verbosity = Literal["quiet", "normal", "verbose"]


class TextReportRenderer:
    """
    Human-readable CLI output. Pure rendering: does not sort or mutate.

    Verbosity levels:
    - quiet: one-line summary only
    - normal: summary + violations (no keys/context)
    - verbose: everything (header, keys, context, suggestions)
    """

    def __init__(self, verbosity: Verbosity = "normal"):
        self.verbosity = verbosity

    def render(self, report: Report) -> str:
        if self.verbosity == "quiet":
            return self._render_quiet(report)
        elif self.verbosity == "verbose":
            return self._render_verbose(report)
        else:
            return self._render_normal(report)

    def _render_quiet(self, report: Report) -> str:
        """One-line summary output."""
        s = report.summary
        if s.total_violations == 0 and s.engine_errors == 0:
            return "✓ No violations\n"

        parts = []
        if s.total_violations > 0:
            sev_parts = [f"{v} {k}" for k, v in sorted(s.by_severity.items()) if v > 0]
            status_parts = [f"{v} {k}" for k, v in sorted(s.by_status.items()) if v > 0]
            parts.append(f"{s.total_violations} violations ({', '.join(sev_parts)}) [{', '.join(status_parts)}]")
        if s.engine_errors > 0:
            parts.append(f"{s.engine_errors} errors")

        return f"✗ {', '.join(parts)}\n"

    def _render_normal(self, report: Report) -> str:
        """Default output: summary + violations without extra details."""
        lines: list[str] = []

        # Summary line
        s = report.summary
        if s.total_violations == 0 and s.engine_errors == 0:
            lines.append("✓ No violations")
        else:
            parts = []
            if s.total_violations > 0:
                sev_parts = [f"{v} {k}" for k, v in sorted(s.by_severity.items()) if v > 0]
                parts.append(f"{s.total_violations} violations ({', '.join(sev_parts)})")
            if s.engine_errors > 0:
                parts.append(f"{s.engine_errors} errors")
            lines.append(f"✗ {', '.join(parts)}")

        lines.append("")

        # Engine errors (always show - they're important)
        if report.engine_errors:
            for e in report.engine_errors:
                lines.extend(self._render_engine_error(e, verbose=False))
            lines.append("")

        # Violations (concise)
        for v in report.violations:
            lines.extend(self._render_violation(v, verbosity="normal"))

        return "\n".join(lines).rstrip() + "\n"

    def _render_verbose(self, report: Report) -> str:
        """Full output with all details."""
        lines: list[str] = []

        # Header
        lines.append(f"{report.tool} {report.version}")
        run = report.run
        lines.append(f"repo: {run.repo_root}")
        if run.branch:
            lines.append(f"branch: {run.branch}")
        if run.commit:
            lines.append(f"commit: {run.commit}")
        if run.mode:
            lines.append(f"mode: {run.mode}")
        if run.baseline_ref:
            lines.append(f"baseline: {run.baseline_ref}")
        if run.created_at:
            lines.append(f"created_at: {run.created_at}")

        lines.append("")

        # Diff summary (optional)
        if report.diff is not None:
            d = report.diff
            lines.append("Diff:")
            lines.append(f"  nodes: +{d.nodes_added}  -{d.nodes_removed}")
            lines.append(f"  edges: +{d.edges_added}  -{d.edges_removed}")
            lines.append("")

        # Summary
        s = report.summary
        lines.append("Summary:")
        lines.append(f"  violations: {s.total_violations}")
        lines.append(f"  engine_errors: {s.engine_errors}")

        if s.by_severity:
            sev_str = "  by_severity: " + ", ".join(f"{k}={v}" for k, v in sorted(s.by_severity.items()))
            lines.append(sev_str)

        if s.by_status:
            st_str = "  by_status: " + ", ".join(f"{k}={v}" for k, v in sorted(s.by_status.items()))
            lines.append(st_str)

        lines.append("")

        # Engine errors
        if report.engine_errors:
            lines.append("Engine Errors:")
            for e in report.engine_errors:
                lines.extend(self._render_engine_error(e, verbose=True))
            lines.append("")

        # Violations
        if report.violations:
            lines.append("Violations:")
            for v in report.violations:
                lines.extend(self._render_violation(v, verbosity="verbose"))
        else:
            lines.append("No violations found.")

        return "\n".join(lines).rstrip() + "\n"

    def _render_engine_error(self, e: EngineError, verbose: bool) -> list[str]:
        out: list[str] = []
        loc = ""
        if e.location is not None:
            loc = f"{e.location.file}:{e.location.line}:{e.location.column}"
        header = f"  ! {e.type}"
        if loc:
            header += f" @ {loc}"
        out.append(header)
        out.append(f"    {e.message}")
        if verbose and e.details:
            for k in sorted(e.details.keys()):
                out.append(f"    {k}: {e.details[k]!r}")
        return out

    def _render_violation(self, v: Violation, verbosity: Verbosity) -> list[str]:
        out: list[str] = []

        sev = v.rule.severity.value if hasattr(v.rule.severity, "value") else str(v.rule.severity)
        loc = ""
        if v.location is not None:
            loc = f"{v.location.file}:{v.location.line}:{v.location.column}"

        header = f"  ✗ {sev.upper()} [{v.rule.id}] {v.rule.name}"
        if loc:
            header += f" @ {loc}"
        out.append(header)

        # Always show status
        out.append(f"    status: {v.status}")

        out.append(f"    {v.message}")

        # Show suggestion in normal and verbose modes
        if verbosity in ("normal", "verbose") and v.suggestion:
            out.append(f"    suggestion: {v.suggestion}")

        # Show key and context only in verbose mode
        if verbosity == "verbose":
            if v.violation_key:
                out.append(f"    key: {v.violation_key}")

            if v.context:
                for k in sorted(v.context.keys()):
                    out.append(f"    {k}: {v.context[k]!r}")

        return out
