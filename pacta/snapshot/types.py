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
from typing import TYPE_CHECKING, Any, Literal

from pacta.ir.types import IREdge, IRNode

if TYPE_CHECKING:
    pass

# Snapshot references

SnapshotRef = str
"""
A snapshot reference identifier.

Examples:
- "latest"
- "baseline"
- "main"
- "commit:abc123"
- "2025-01-15T12:30:00Z"
"""

# Snapshot metadata


@dataclass(frozen=True, slots=True)
class SnapshotMeta:
    """
    Metadata describing when and how the snapshot was produced.
    """

    repo_root: str
    commit: str | None = None
    branch: str | None = None
    created_at: str | None = None  # ISO-8601
    tool_version: str | None = None
    model_version: int | None = None

    extra: Mapping[str, Any] = field(default_factory=dict)


# Snapshot (core persisted object)


@dataclass(frozen=True, slots=True)
class Snapshot:
    """
    Immutable architecture snapshot.

    Snapshot contains:
      - enriched IR nodes
      - enriched IR edges
      - violations (for baseline comparison)
      - metadata

    Snapshot is:
      - deterministic
      - serializable
      - diffable
    """

    schema_version: int
    meta: SnapshotMeta

    nodes: tuple[IRNode, ...]
    edges: tuple[IREdge, ...]

    # Violations are stored for baseline comparison
    violations: tuple[Any, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "meta": {
                "repo_root": self.meta.repo_root,
                "commit": self.meta.commit,
                "branch": self.meta.branch,
                "created_at": self.meta.created_at,
                "tool_version": self.meta.tool_version,
                "model_version": self.meta.model_version,
                "extra": dict(self.meta.extra),
            },
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "violations": [v.to_dict() if hasattr(v, "to_dict") else v for v in self.violations],
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "Snapshot":
        from pacta.reporting.types import Violation

        meta = data["meta"]

        # Parse violations if present
        raw_violations = data.get("violations", [])
        violations: tuple[Any, ...] = ()
        if raw_violations:
            parsed = []
            for v in raw_violations:
                if isinstance(v, dict):
                    try:
                        parsed.append(Violation.from_dict(v))
                    except Exception:
                        # Keep as dict if parsing fails
                        parsed.append(v)
                else:
                    parsed.append(v)
            violations = tuple(parsed)

        return Snapshot(
            schema_version=int(data["schema_version"]),
            meta=SnapshotMeta(
                repo_root=str(meta["repo_root"]),
                commit=meta.get("commit"),
                branch=meta.get("branch"),
                created_at=meta.get("created_at"),
                tool_version=meta.get("tool_version"),
                model_version=meta.get("model_version"),
                extra=meta.get("extra") or {},
            ),
            nodes=tuple(IRNode.from_dict(n) for n in data.get("nodes", [])),
            edges=tuple(IREdge.from_dict(e) for e in data.get("edges", [])),
            violations=violations,
        )

    @staticmethod
    def empty(repo_root: str) -> "Snapshot":
        """
        Convenience constructor for empty snapshot.
        """
        return Snapshot(
            schema_version=1,
            meta=SnapshotMeta(repo_root=repo_root),
            nodes=(),
            edges=(),
            violations=(),
        )


# Snapshot diff (structural)


@dataclass(frozen=True, slots=True)
class SnapshotDiff:
    """
    Structural difference between two snapshots.

    This is intentionally factual and rule-agnostic.
    """

    nodes_added: int
    nodes_removed: int
    edges_added: int
    edges_removed: int

    # Optional detailed breakdown (IDs, edges, etc.)
    details: Mapping[str, Any] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return self.nodes_added == 0 and self.nodes_removed == 0 and self.edges_added == 0 and self.edges_removed == 0


# Violation baseline status

ViolationStatus = Literal[
    "new",
    "existing",
    "fixed",
    "unknown",
]
"""
Status of a violation relative to a baseline snapshot.
"""

# Baseline comparison result


@dataclass(frozen=True, slots=True)
class BaselineResult:
    """
    Result of baseline comparison.
    """

    new: int
    existing: int
    fixed: int
    unknown: int

    def to_dict(self) -> dict[str, int]:
        return {
            "new": self.new,
            "existing": self.existing,
            "fixed": self.fixed,
            "unknown": self.unknown,
        }
