from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from pacta.reporting._extract import get_field
from pacta.reporting.types import (
    DiffSummary,
    EngineError,
    Report,
    RunInfo,
    Severity,
    Summary,
    Violation,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _severity_str(sev: Any) -> str:
    if isinstance(sev, Severity):
        return sev.value
    if hasattr(sev, "value"):
        return str(sev.value)
    return str(sev)


def _violation_sort_key(v: Violation) -> tuple:
    # deterministic ordering for renderers and JSON output
    loc = v.location
    file = loc.file if loc else ""
    line = loc.line if loc else -1
    col = loc.column if loc else -1
    return (
        _severity_str(v.rule.severity),
        v.rule.id,
        v.status,
        file,
        line,
        col,
        v.violation_key or "",
        v.message,
    )


def _engine_error_sort_key(e: EngineError) -> tuple:
    loc = e.location
    file = loc.file if loc else ""
    line = loc.line if loc else -1
    col = loc.column if loc else -1
    return (e.type, file, line, col, e.message)


class DefaultReportBuilder:
    """
    Build a pacta.reporting.types.Report from engine outputs.

    Accepts:
    - violations: Sequence[Violation] OR Sequence[dict/object]
    - engine_errors: Sequence[EngineError] OR Sequence[dict/object]
    - diff: DiffSummary OR dict/object or None

    Normalizes:
    - created_at (if missing)
    - stable ordering
    - Summary counts
    """

    def __init__(self, *, tool: str = "pacta", version: str = "0.0.4") -> None:
        self._tool = tool
        self._version = version

    def build(
        self,
        *,
        run: RunInfo,
        violations: Sequence[Any] = (),
        engine_errors: Sequence[Any] = (),
        diff: Any | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Report:
        run_norm = self._normalize_run(run, metadata=metadata)
        viol_norm = tuple(self._normalize_violation(v) for v in violations)
        err_norm = tuple(self._normalize_engine_error(e) for e in engine_errors)
        diff_norm = self._normalize_diff(diff)

        # deterministic ordering
        viol_norm = tuple(sorted(viol_norm, key=_violation_sort_key))
        err_norm = tuple(sorted(err_norm, key=_engine_error_sort_key))

        summary = self._build_summary(viol_norm, err_norm)

        return Report(
            tool=self._tool,
            version=self._version,
            run=run_norm,
            summary=summary,
            violations=viol_norm,
            engine_errors=err_norm,
            diff=diff_norm,
        )

    def _normalize_run(self, run: RunInfo, *, metadata: Mapping[str, Any] | None) -> RunInfo:
        # RunInfo is frozen; we return a copy if needed
        created_at = run.created_at or _now_iso()
        md = dict(run.metadata)
        if metadata:
            md.update(dict(metadata))
        return replace(run, created_at=created_at, metadata=md)

    def _normalize_violation(self, v: Any) -> Violation:
        if isinstance(v, Violation):
            return v

        # dict/object normalization into Violation dataclass
        # We expect it’s already in report.types-ish shape.
        rule = get_field(v, "rule")
        if rule is None:
            raise TypeError("Violation must have a 'rule' field/object.")

        # If rule is already RuleRef, it's fine; otherwise it must be dict/object convertible
        from pacta.reporting.types import ReportLocation, RuleRef

        if not isinstance(rule, RuleRef):
            rule = RuleRef(
                id=str(get_field(rule, "id")),
                name=str(get_field(rule, "name", default=get_field(rule, "id", default=""))),
                severity=Severity(str(get_field(rule, "severity", default="error"))),
                description=get_field(rule, "description"),
            )

        loc = get_field(v, "location")
        if loc is None:
            location = None
        elif isinstance(loc, ReportLocation):
            location = loc
        else:
            location = ReportLocation(
                file=str(get_field(loc, "file")),
                line=int(get_field(loc, "line", default=1)),
                column=int(get_field(loc, "column", default=1)),
                end_line=get_field(loc, "end_line"),
                end_column=get_field(loc, "end_column"),
            )

        return Violation(
            rule=rule,
            message=str(get_field(v, "message", default="")),
            status=str(get_field(v, "status", default="unknown")),  # type: ignore[invalid-argument-type]
            location=location,
            context=dict(get_field(v, "context", default={}) or {}),
            violation_key=get_field(v, "violation_key"),
            suggestion=get_field(v, "suggestion"),
        )

    def _normalize_engine_error(self, e: Any) -> EngineError:
        if isinstance(e, EngineError):
            return e

        from pacta.reporting.types import ReportLocation

        loc = get_field(e, "location")
        if loc is None:
            location = None
        elif isinstance(loc, ReportLocation):
            location = loc
        else:
            location = ReportLocation(
                file=str(get_field(loc, "file")),
                line=int(get_field(loc, "line", default=1)),
                column=int(get_field(loc, "column", default=1)),
                end_line=get_field(loc, "end_line"),
                end_column=get_field(loc, "end_column"),
            )

        return EngineError(
            type=str(get_field(e, "type", default="runtime_error")),  # type: ignore[invalid-argument-type]
            message=str(get_field(e, "message", default="")),
            location=location,
            details=dict(get_field(e, "details", default={}) or {}),
        )

    def _normalize_diff(self, diff: Any | None) -> DiffSummary | None:
        if diff is None:
            return None
        if isinstance(diff, DiffSummary):
            return diff

        return DiffSummary(
            nodes_added=int(get_field(diff, "nodes_added", default=get_field(diff, "nodesAdded", default=0))),
            nodes_removed=int(get_field(diff, "nodes_removed", default=get_field(diff, "nodesRemoved", default=0))),
            edges_added=int(get_field(diff, "edges_added", default=get_field(diff, "edgesAdded", default=0))),
            edges_removed=int(get_field(diff, "edges_removed", default=get_field(diff, "edgesRemoved", default=0))),
        )

    def _build_summary(self, violations: Sequence[Violation], engine_errors: Sequence[EngineError]) -> Summary:
        by_sev = Counter()
        by_status = Counter()
        by_rule = Counter()

        for v in violations:
            by_sev[_severity_str(v.rule.severity)] += 1
            by_status[str(v.status)] += 1
            by_rule[str(v.rule.id)] += 1

        return Summary(
            total_violations=len(violations),
            by_severity=dict(sorted(by_sev.items(), key=lambda kv: kv[0])),
            by_status=dict(sorted(by_status.items(), key=lambda kv: kv[0])),
            by_rule=dict(sorted(by_rule.items(), key=lambda kv: kv[0])),
            engine_errors=len(engine_errors),
        )
