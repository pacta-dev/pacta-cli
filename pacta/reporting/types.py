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

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import auto
from typing import Any, Literal

from pacta.utils.enum import StrEnum

# Severity enum


class Severity(StrEnum):
    """
    Severity level of an architecture violation.

    Ordering (from strongest to weakest):
      ERROR   → build-breaking
      WARNING → visible but non-blocking
      INFO    → informational only

    Severity is intentionally:
      - language-agnostic
      - stable across versions
      - string-based for JSON/CLI/SaaS compatibility
    """

    ERROR = auto()
    WARNING = auto()
    INFO = auto()

    def is_blocking(self) -> bool:
        """
        Whether this severity should fail CI by default.
        """
        return self == Severity.ERROR

    @staticmethod
    def ordered() -> tuple["Severity", ...]:
        """
        Severity ordering from highest to lowest importance.
        """
        return (Severity.ERROR, Severity.WARNING, Severity.INFO)

    @classmethod
    def from_str(cls, value: str) -> "Severity":
        """
        Parse severity from string (case-insensitive).

        Raises:
            ValueError if invalid severity.
        """
        value = value.lower()
        for sev in Severity:
            if sev.value == value:
                return sev
        raise ValueError(f"Invalid severity: {value}")


# Common location structure


@dataclass(frozen=True, slots=True)
class ReportLocation:
    """
    Location in source code, stable for rendering and tooling.
    """

    file: str
    line: int
    column: int = 1

    end_line: int | None = None
    end_column: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "ReportLocation":
        return ReportLocation(
            file=data["file"],
            line=data["line"],
            column=data.get("column", 1),
            end_line=data.get("end_line"),
            end_column=data.get("end_column"),
        )


# Engine errors (not violations)

EngineErrorType = Literal[
    "config_error",
    "parse_error",
    "rules_error",
    "analyzer_error",
    "runtime_error",
]


@dataclass(frozen=True, slots=True)
class EngineError:
    """
    Represents internal failures that may affect analysis completeness.
    These are NOT architectural violations. They are tool/engine errors.

    Examples:
    - invalid architecture.yaml
    - rules DSL parse error
    - analyzer crash on a file
    """

    type: EngineErrorType
    message: str
    location: ReportLocation | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "message": self.message,
            "location": None if self.location is None else self.location.to_dict(),
            "details": dict(self.details),
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "EngineError":
        loc = data.get("location")
        return EngineError(
            type=data["type"],
            message=data["message"],
            location=None if loc is None else ReportLocation.from_dict(loc),
            details=dict(data.get("details", {})),
        )


# Violations (rule matches)

ViolationStatus = Literal["new", "existing", "fixed", "unknown"]


@dataclass(frozen=True, slots=True)
class RuleRef:
    """
    Minimal rule metadata embedded into a violation for reporting.
    """

    id: str
    name: str
    severity: Severity
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity.value,
            "description": self.description,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "RuleRef":
        return RuleRef(
            id=data["id"],
            name=data["name"],
            severity=Severity(data["severity"]),
            description=data.get("description"),
        )


@dataclass(frozen=True, slots=True)
class Violation:
    """
    A concrete rule match against the architecture.

    `violation_key` MUST be stable across runs for baseline support.
    """

    rule: RuleRef
    message: str
    status: ViolationStatus = "unknown"

    location: ReportLocation | None = None

    # "from/to" style context is useful for dependency violations
    context: Mapping[str, Any] = field(default_factory=dict)

    # Stable identity used for baselines/diffs
    violation_key: str | None = None

    # Optional: how to fix
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule.to_dict(),
            "message": self.message,
            "status": self.status,
            "location": None if self.location is None else self.location.to_dict(),
            "context": dict(self.context),
            "violation_key": self.violation_key,
            "suggestion": self.suggestion,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "Violation":
        loc = data.get("location")
        return Violation(
            rule=RuleRef.from_dict(data["rule"]),
            message=data["message"],
            status=data.get("status", "unknown"),
            location=None if loc is None else ReportLocation.from_dict(loc),
            context=dict(data.get("context", {})),
            violation_key=data.get("violation_key"),
            suggestion=data.get("suggestion"),
        )


# Run metadata


@dataclass(frozen=True, slots=True)
class RunInfo:
    """
    Provenance information for this scan run.
    """

    repo_root: str
    commit: str | None = None
    branch: str | None = None

    model_file: str | None = None
    rules_files: tuple[str, ...] = ()

    baseline_ref: str | None = None
    mode: Literal["full", "changed_only"] = "full"

    created_at: str | None = None  # ISO-8601
    tool_version: str | None = None

    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_root": self.repo_root,
            "commit": self.commit,
            "branch": self.branch,
            "model_file": self.model_file,
            "rules_files": list(self.rules_files),
            "baseline_ref": self.baseline_ref,
            "mode": self.mode,
            "created_at": self.created_at,
            "tool_version": self.tool_version,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "RunInfo":
        return RunInfo(
            repo_root=data["repo_root"],
            commit=data.get("commit"),
            branch=data.get("branch"),
            model_file=data.get("model_file"),
            rules_files=tuple(data.get("rules_files", ())),
            baseline_ref=data.get("baseline_ref"),
            mode=data.get("mode", "full"),
            created_at=data.get("created_at"),
            tool_version=data.get("tool_version"),
            metadata=dict(data.get("metadata", {})),
        )


# Summary (counts + groupings)


@dataclass(frozen=True, slots=True)
class Summary:
    """
    Aggregated report statistics.
    """

    total_violations: int
    by_severity: Mapping[str, int]
    by_status: Mapping[str, int]
    by_rule: Mapping[str, int]

    engine_errors: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_violations": self.total_violations,
            "by_severity": dict(self.by_severity),
            "by_status": dict(self.by_status),
            "by_rule": dict(self.by_rule),
            "engine_errors": self.engine_errors,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "Summary":
        return Summary(
            total_violations=data["total_violations"],
            by_severity=dict(data.get("by_severity", {})),
            by_status=dict(data.get("by_status", {})),
            by_rule=dict(data.get("by_rule", {})),
            engine_errors=data.get("engine_errors", 0),
        )


# Diff summary (optional)


@dataclass(frozen=True, slots=True)
class DiffSummary:
    """
    Optional high-level diff summary suitable for CLI/PR comment.
    """

    nodes_added: int
    nodes_removed: int
    edges_added: int
    edges_removed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes_added": self.nodes_added,
            "nodes_removed": self.nodes_removed,
            "edges_added": self.edges_added,
            "edges_removed": self.edges_removed,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "DiffSummary":
        return DiffSummary(
            nodes_added=data["nodes_added"],
            nodes_removed=data["nodes_removed"],
            edges_added=data["edges_added"],
            edges_removed=data["edges_removed"],
        )


# Final report object


@dataclass(frozen=True, slots=True)
class Report:
    """
    Final output of the engine (in-memory).
    Can be rendered to text/json/sarif.
    """

    tool: str
    version: str
    run: RunInfo

    summary: Summary
    violations: tuple[Violation, ...] = ()
    engine_errors: tuple[EngineError, ...] = ()

    diff: DiffSummary | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "version": self.version,
            "run": self.run.to_dict(),
            "summary": self.summary.to_dict(),
            "violations": [v.to_dict() for v in self.violations],
            "engine_errors": [e.to_dict() for e in self.engine_errors],
            "diff": None if self.diff is None else self.diff.to_dict(),
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "Report":
        diff = data.get("diff")

        return Report(
            tool=data["tool"],
            version=data["version"],
            run=RunInfo.from_dict(data["run"]),
            summary=Summary.from_dict(data["summary"]),
            violations=tuple(Violation.from_dict(v) for v in data.get("violations", ())),
            engine_errors=tuple(EngineError.from_dict(e) for e in data.get("engine_errors", ())),
            diff=None if diff is None else DiffSummary.from_dict(diff),
        )
