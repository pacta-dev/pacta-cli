from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from pacta.reporting.types import Report, TrendPoint, TrendSummary
from pacta.snapshot.store import FsSnapshotStore


def attach_trends(
    report: Report,
    *,
    repo_root: str,
    last: int = 5,
) -> Report:
    """
    Load recent snapshots and attach a TrendSummary to the report.

    Returns the report unchanged if no history is available.
    """
    try:
        store = FsSnapshotStore(repo_root=repo_root)
        objects = store.list_objects()
    except Exception:
        return report

    if len(objects) < 2:
        return report

    # Take the most recent N entries (list_objects returns newest-first)
    entries = objects[:last]
    # Reverse to chronological order (oldest first)
    entries = list(reversed(entries))

    points: list[TrendPoint] = []
    for _, snapshot in entries:
        meta = snapshot.meta
        node_count = float(len(snapshot.nodes))
        edge_count = float(len(snapshot.edges))
        violation_count = float(len(snapshot.violations))
        density = round(edge_count / node_count, 2) if node_count > 0 else 0.0

        label = _format_label(meta.created_at)
        points.append(
            TrendPoint(
                label=label,
                violations=violation_count,
                nodes=node_count,
                edges=edge_count,
                density=density,
            )
        )

    first = points[0]
    last_pt = points[-1]

    trends = TrendSummary(
        points=tuple(points),
        violation_change=last_pt.violations - first.violations,
        node_change=last_pt.nodes - first.nodes,
        edge_change=last_pt.edges - first.edges,
        density_change=round(last_pt.density - first.density, 2),
    )

    return replace(report, trends=trends)


def _format_label(created_at: str | None) -> str:
    if not created_at or "T" not in created_at:
        return created_at or "unknown"
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return dt.strftime("%b %d")
    except ValueError:
        return created_at.split("T")[0]
