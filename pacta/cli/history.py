import json
import sys
from datetime import datetime
from pathlib import Path

from pacta.cli._ascii_chart import render_line_chart, render_trend_summary
from pacta.cli._io import ensure_repo_root
from pacta.cli.exitcodes import EXIT_OK
from pacta.snapshot import Snapshot
from pacta.snapshot.store import FsSnapshotStore


def show(
    *,
    path: str,
    last: int | None = None,
    since: str | None = None,
    branch: str | None = None,
    format: str = "text",
) -> int:
    """
    Show architecture history (list of snapshots).

    Args:
        path: Repository root path
        last: Show only last N entries
        since: Show entries since date (ISO-8601)
        branch: Filter by branch name
        format: Output format (text or json)
    """
    repo_root = Path(ensure_repo_root(path))
    store = FsSnapshotStore(repo_root=str(repo_root))

    # Get all objects sorted by timestamp
    objects = store.list_objects()

    if not objects:
        if format == "json":
            print(json.dumps({"entries": [], "count": 0}))
        else:
            print("No history entries found.")
            print("Run 'pacta scan' to create snapshots.")
        return EXIT_OK

    # Apply filters
    entries = []
    for short_hash, snapshot in objects:
        meta = snapshot.meta

        # Filter by branch if specified
        if branch and meta.branch != branch:
            continue

        # Filter by since date if specified
        if since and meta.created_at:
            try:
                since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                created_dt = datetime.fromisoformat(meta.created_at.replace("Z", "+00:00"))
                # Normalize to compare: strip timezone info for comparison
                since_naive = since_dt.replace(tzinfo=None) if since_dt.tzinfo else since_dt
                created_naive = created_dt.replace(tzinfo=None) if created_dt.tzinfo else created_dt
                if created_naive < since_naive:
                    continue
            except ValueError:
                pass  # Invalid date format, skip filter

        entries.append((short_hash, snapshot))

    # Apply limit
    if last and last > 0:
        entries = entries[:last]

    # Get refs for display
    refs = store.list_refs()
    hash_to_refs: dict[str, list[str]] = {}
    for ref_name, ref_hash in refs.items():
        if ref_hash not in hash_to_refs:
            hash_to_refs[ref_hash] = []
        hash_to_refs[ref_hash].append(ref_name)

    if format == "json":
        _output_json(entries, hash_to_refs)
    else:
        _output_text(entries, hash_to_refs)

    return EXIT_OK


def _output_text(
    entries: list[tuple[str, "Snapshot"]],  # noqa: F821
    hash_to_refs: dict[str, list[str]],
) -> None:
    """Output history in text format."""
    print(f"Architecture Timeline ({len(entries)} entries)")
    print("=" * 60)
    print()

    for short_hash, snapshot in entries:
        meta = snapshot.meta
        refs_list = hash_to_refs.get(short_hash, [])

        # Format timestamp
        timestamp = meta.created_at or "unknown"
        if "T" in timestamp:
            timestamp = timestamp.split("T")[0]  # Just date

        # Format commit (short)
        commit = (meta.commit or "-------")[:7]

        # Format branch
        branch = meta.branch or "?"

        # Counts
        node_count = len(snapshot.nodes)
        edge_count = len(snapshot.edges)
        violation_count = len(snapshot.violations)

        # Refs
        refs_str = f" ({', '.join(refs_list)})" if refs_list else ""

        # Output line
        print(
            f"{short_hash}  {timestamp}  {commit}  {branch:<12}  "
            f"{node_count:>3} nodes  {edge_count:>3} edges  "
            f"{violation_count:>2} violations{refs_str}"
        )

    print()


def _output_json(
    entries: list[tuple[str, "Snapshot"]],  # noqa: F821
    hash_to_refs: dict[str, list[str]],
) -> None:
    """Output history in JSON format."""
    result = {
        "entries": [],
        "count": len(entries),
    }

    for short_hash, snapshot in entries:
        meta = snapshot.meta
        refs_list = hash_to_refs.get(short_hash, [])

        # Count violations by severity
        violations_by_severity: dict[str, int] = {}
        for v in snapshot.violations:
            if hasattr(v, "rule") and hasattr(v.rule, "severity"):
                sev = str(v.rule.severity.value) if hasattr(v.rule.severity, "value") else str(v.rule.severity)
            elif isinstance(v, dict) and "rule" in v and "severity" in v["rule"]:
                sev = v["rule"]["severity"]
            else:
                sev = "unknown"
            violations_by_severity[sev] = violations_by_severity.get(sev, 0) + 1

        entry = {
            "hash": short_hash,
            "timestamp": meta.created_at,
            "commit": meta.commit,
            "branch": meta.branch,
            "refs": refs_list,
            "node_count": len(snapshot.nodes),
            "edge_count": len(snapshot.edges),
            "violation_count": len(snapshot.violations),
            "violations_by_severity": violations_by_severity,
        }
        result["entries"].append(entry)  # type: ignore[possibly-missing-attribute]

    print(json.dumps(result, indent=2, default=str))


def export(
    *,
    path: str,
    format: str = "json",
    output: str | None = None,
) -> int:
    """
    Export full history data for external processing.

    Args:
        path: Repository root path
        format: Export format (json or jsonl)
        output: Output file path (default: stdout)
    """
    repo_root = Path(ensure_repo_root(path))
    store = FsSnapshotStore(repo_root=str(repo_root))

    objects = store.list_objects()
    refs = store.list_refs()

    # Build hash to refs mapping
    hash_to_refs: dict[str, list[str]] = {}
    for ref_name, ref_hash in refs.items():
        if ref_hash not in hash_to_refs:
            hash_to_refs[ref_hash] = []
        hash_to_refs[ref_hash].append(ref_name)

    # Build export data
    entries = []
    for short_hash, snapshot in objects:
        meta = snapshot.meta

        entry = {
            "hash": short_hash,
            "timestamp": meta.created_at,
            "commit": meta.commit,
            "branch": meta.branch,
            "refs": hash_to_refs.get(short_hash, []),
            "repo_root": meta.repo_root,
            "tool_version": meta.tool_version,
            "node_count": len(snapshot.nodes),
            "edge_count": len(snapshot.edges),
            "violations": [v.to_dict() if hasattr(v, "to_dict") else v for v in snapshot.violations],
        }
        entries.append(entry)

    # Output
    out_stream = open(output, "w") if output else sys.stdout

    try:
        if format == "jsonl":
            for entry in entries:
                out_stream.write(json.dumps(entry, default=str) + "\n")
        else:
            result = {
                "version": 1,
                "exported_at": datetime.now().isoformat(),
                "repo_root": str(repo_root),
                "refs": refs,
                "entries": entries,
            }
            out_stream.write(json.dumps(result, indent=2, default=str) + "\n")
    finally:
        if output:
            out_stream.close()

    if output:
        print(f"Exported {len(entries)} entries to {output}", file=sys.stderr)

    return EXIT_OK


def trends(
    *,
    path: str,
    metric: str = "violations",
    last: int | None = None,
    since: str | None = None,
    branch: str | None = None,
    width: int = 60,
    format: str = "text",
    output: str | None = None,
) -> int:
    """
    Show metric trends over time.

    Args:
        path: Repository root path
        metric: Metric to track (violations, nodes, edges, density)
        last: Show only last N entries
        since: Show entries since date (ISO-8601)
        branch: Filter by branch name
        width: Chart width (default: 60)
        format: Output format (text or json)
        output: Output file for image export (PNG/SVG)
    """
    repo_root = Path(ensure_repo_root(path))
    store = FsSnapshotStore(repo_root=str(repo_root))

    # Get all objects sorted by timestamp
    objects = store.list_objects()

    if not objects:
        if format == "json":
            print(json.dumps({"metric": metric, "data_points": [], "count": 0}))
        else:
            print("No history entries found.")
            print("Run 'pacta scan' to create snapshots.")
        return EXIT_OK

    # Apply filters (reuse logic from show())
    entries = _filter_entries(objects, branch=branch, since=since, last=last)

    if not entries:
        if format == "json":
            print(json.dumps({"metric": metric, "data_points": [], "count": 0}))
        else:
            print("No matching entries found after applying filters.")
        return EXIT_OK

    # Reverse to chronological order (oldest first) for trend display
    entries = list(reversed(entries))

    # Extract metric values
    values: list[float] = []
    labels: list[str] = []

    for _, snapshot in entries:
        meta = snapshot.meta
        value = _extract_metric(snapshot, metric)
        values.append(value)

        # Format label (short date)
        timestamp = meta.created_at or "unknown"
        if "T" in timestamp:
            label = timestamp.split("T")[0]  # Just date (YYYY-MM-DD)
            # Shorten to MMM DD format
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                label = dt.strftime("%b %d")
            except ValueError:
                pass
        else:
            label = timestamp[:10]
        labels.append(label)

    # Handle output
    if output:
        # Image export using matplotlib
        _output_trends_image(metric, values, labels, output)
        print(f"Saved trends chart to {output}")
    elif format == "json":
        _output_trends_json(metric, values, labels, entries)
    else:
        _output_trends_text(metric, values, labels, width)

    return EXIT_OK


def _filter_entries(
    objects: list[tuple[str, "Snapshot"]],
    *,
    branch: str | None = None,
    since: str | None = None,
    last: int | None = None,
) -> list[tuple[str, "Snapshot"]]:
    """Filter entries by branch, date, and limit."""
    entries = []

    for short_hash, snapshot in objects:
        meta = snapshot.meta

        # Filter by branch if specified
        if branch and meta.branch != branch:
            continue

        # Filter by since date if specified
        if since and meta.created_at:
            try:
                since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                created_dt = datetime.fromisoformat(meta.created_at.replace("Z", "+00:00"))
                # Normalize to compare: strip timezone info for comparison
                since_naive = since_dt.replace(tzinfo=None) if since_dt.tzinfo else since_dt
                created_naive = created_dt.replace(tzinfo=None) if created_dt.tzinfo else created_dt
                if created_naive < since_naive:
                    continue
            except ValueError:
                pass  # Invalid date format, skip filter

        entries.append((short_hash, snapshot))

    # Apply limit
    if last and last > 0:
        entries = entries[:last]

    return entries


def _extract_metric(snapshot: "Snapshot", metric: str) -> float:
    """Extract a metric value from a snapshot."""
    if metric == "violations":
        return float(len(snapshot.violations))
    elif metric == "nodes":
        return float(len(snapshot.nodes))
    elif metric == "edges":
        return float(len(snapshot.edges))
    elif metric == "density":
        # Density = edges / nodes (coupling ratio)
        node_count = len(snapshot.nodes)
        edge_count = len(snapshot.edges)
        if node_count == 0:
            return 0.0
        return round(edge_count / node_count, 2)
    else:
        return 0.0


def _output_trends_text(
    metric: str,
    values: list[float],
    labels: list[str],
    width: int,
) -> None:
    """Output trends in text format with ASCII chart."""
    metric_titles = {
        "violations": "Violations Trend",
        "nodes": "Node Count Trend",
        "edges": "Edge Count Trend",
        "density": "Density Trend (edges/nodes)",
    }

    title = f"{metric_titles.get(metric, metric)} ({len(values)} entries)"

    # Render chart
    chart = render_line_chart(values, labels, width=width, title=title)
    print(chart)

    # Render summary
    summary = render_trend_summary(values, labels, metric)
    print(summary)


def _output_trends_json(
    metric: str,
    values: list[float],
    labels: list[str],
    entries: list[tuple[str, "Snapshot"]],
) -> None:
    """Output trends in JSON format."""
    data_points = []

    for i, (short_hash, snapshot) in enumerate(entries):
        data_points.append(
            {
                "hash": short_hash,
                "timestamp": snapshot.meta.created_at,
                "label": labels[i],
                "value": values[i],
            }
        )

    first_val = values[0] if values else None
    last_val = values[-1] if values else None
    diff = (last_val - first_val) if (first_val is not None and last_val is not None) else None

    result = {
        "metric": metric,
        "count": len(values),
        "data_points": data_points,
        "summary": {
            "first": first_val,
            "last": last_val,
            "change": diff,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "average": round(sum(values) / len(values), 2) if values else None,
        },
    }

    print(json.dumps(result, indent=2, default=str))


def _output_trends_image(
    metric: str,
    values: list[float],
    labels: list[str],
    output_path: str,
) -> None:
    """Output trends as an image file using matplotlib."""
    from pacta.cli._mpl_chart import render_trends_chart

    metric_titles = {
        "violations": "Violations Trend",
        "nodes": "Node Count Trend",
        "edges": "Edge Count Trend",
        "density": "Density Trend (edges/nodes)",
    }

    title = f"{metric_titles.get(metric, metric)} ({len(values)} entries)"

    render_trends_chart(
        values=values,
        labels=labels,
        metric=metric,
        output_path=output_path,
        title=title,
    )
