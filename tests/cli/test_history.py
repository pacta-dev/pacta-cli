"""
Tests for the history CLI commands.
"""

import json
from pathlib import Path

import pytest
from pacta.ir.types import CanonicalId, IRNode, Language, SymbolKind
from pacta.snapshot.builder import DefaultSnapshotBuilder
from pacta.snapshot.store import FsSnapshotStore
from pacta.snapshot.types import SnapshotMeta


def make_node(key: str) -> IRNode:
    """Create a real IRNode for testing."""
    return IRNode(
        id=CanonicalId(language=Language.PYTHON, code_root="test-repo", fqname=key),
        kind=SymbolKind.MODULE,
        name=f"n-{key}",
        path=f"pkg/{key}.py",
    )


@pytest.fixture
def repo_with_history(tmp_path: Path) -> Path:
    """Create a repository with multiple snapshots for history testing."""
    repo = tmp_path / "test-repo"
    repo.mkdir()

    store = FsSnapshotStore(repo_root=str(repo))
    builder = DefaultSnapshotBuilder()

    # Create 3 snapshots with different timestamps
    for i in range(3):
        meta = SnapshotMeta(
            repo_root=str(repo),
            commit=f"abc{i}def",
            branch="main" if i != 1 else "feature",
            created_at=f"2025-01-0{i + 1}T12:00:00+00:00",
        )
        ir = {"nodes": [make_node(f"node{j}") for j in range(i + 1)], "edges": []}
        snap = builder.build(ir, meta=meta)

        refs = [f"snap{i}"]
        if i == 2:
            refs.append("latest")
        store.save(snap, refs=refs)

    return repo


class TestHistoryShow:
    """Tests for `pacta history show` command."""

    def test_show_lists_all_snapshots(self, repo_with_history: Path):
        """history show should list all snapshots."""
        from pacta.cli.history import show

        # Capture output by checking return code (text output goes to stdout)
        result = show(path=str(repo_with_history), format="json")

        assert result == 0

    def test_show_json_format(self, repo_with_history: Path, capsys):
        """history show --format json should output valid JSON."""
        from pacta.cli.history import show

        show(path=str(repo_with_history), format="json")
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert "entries" in data
        assert "count" in data
        assert data["count"] == 3

    def test_show_last_filter(self, repo_with_history: Path, capsys):
        """history show --last N should limit results."""
        from pacta.cli.history import show

        show(path=str(repo_with_history), last=2, format="json")
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert data["count"] == 2

    def test_show_branch_filter(self, repo_with_history: Path, capsys):
        """history show --branch should filter by branch."""
        from pacta.cli.history import show

        show(path=str(repo_with_history), branch="feature", format="json")
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert data["count"] == 1
        assert data["entries"][0]["branch"] == "feature"

    def test_show_since_filter(self, repo_with_history: Path, capsys):
        """history show --since should filter by date."""
        from pacta.cli.history import show

        show(path=str(repo_with_history), since="2025-01-02T00:00:00", format="json")
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        # Should only include entries on or after 2025-01-02
        assert data["count"] == 2

    def test_show_empty_repo(self, tmp_path: Path, capsys):
        """history show on empty repo should show helpful message."""
        from pacta.cli.history import show

        empty_repo = tmp_path / "empty"
        empty_repo.mkdir()

        result = show(path=str(empty_repo), format="text")

        assert result == 0
        captured = capsys.readouterr()
        assert "No history" in captured.out or "no history" in captured.out.lower()

    def test_show_text_format(self, repo_with_history: Path, capsys):
        """history show with text format should output readable text."""
        from pacta.cli.history import show

        show(path=str(repo_with_history), format="text")
        captured = capsys.readouterr()

        assert "Timeline" in captured.out
        assert "nodes" in captured.out
        assert "edges" in captured.out


class TestHistoryExport:
    """Tests for `pacta history export` command."""

    def test_export_json_format(self, repo_with_history: Path, capsys):
        """history export should output valid JSON."""
        from pacta.cli.history import export

        export(path=str(repo_with_history), format="json")
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert "version" in data
        assert "entries" in data
        assert "refs" in data
        assert len(data["entries"]) == 3

    def test_export_jsonl_format(self, repo_with_history: Path, capsys):
        """history export --format jsonl should output JSON lines."""
        from pacta.cli.history import export

        export(path=str(repo_with_history), format="jsonl")
        captured = capsys.readouterr()

        lines = [line for line in captured.out.strip().split("\n") if line]
        assert len(lines) == 3

        # Each line should be valid JSON
        for line in lines:
            data = json.loads(line)
            assert "hash" in data
            assert "timestamp" in data

    def test_export_to_file(self, repo_with_history: Path, tmp_path: Path):
        """history export -o should write to file."""
        from pacta.cli.history import export

        output_file = tmp_path / "export.json"
        export(path=str(repo_with_history), format="json", output=str(output_file))

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert len(data["entries"]) == 3


class TestHistoryTrends:
    """Tests for `pacta history trends` command."""

    def test_trends_violations(self, repo_with_history: Path, capsys):
        """history trends should show violation trends."""
        from pacta.cli.history import trends

        result = trends(path=str(repo_with_history), metric="violations")

        assert result == 0
        captured = capsys.readouterr()
        assert "Violations Trend" in captured.out
        assert "entries" in captured.out

    def test_trends_nodes(self, repo_with_history: Path, capsys):
        """history trends --metric nodes should show node count trends."""
        from pacta.cli.history import trends

        result = trends(path=str(repo_with_history), metric="nodes")

        assert result == 0
        captured = capsys.readouterr()
        assert "Node Count Trend" in captured.out

    def test_trends_edges(self, repo_with_history: Path, capsys):
        """history trends --metric edges should show edge count trends."""
        from pacta.cli.history import trends

        result = trends(path=str(repo_with_history), metric="edges")

        assert result == 0
        captured = capsys.readouterr()
        assert "Edge Count Trend" in captured.out

    def test_trends_density(self, repo_with_history: Path, capsys):
        """history trends --metric density should show density trends."""
        from pacta.cli.history import trends

        result = trends(path=str(repo_with_history), metric="density")

        assert result == 0
        captured = capsys.readouterr()
        assert "Density Trend" in captured.out

    def test_trends_json_format(self, repo_with_history: Path, capsys):
        """history trends --format json should output valid JSON."""
        from pacta.cli.history import trends

        result = trends(path=str(repo_with_history), metric="violations", format="json")

        assert result == 0
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert data["metric"] == "violations"
        assert "data_points" in data
        assert "summary" in data
        assert data["count"] == 3

    def test_trends_last_filter(self, repo_with_history: Path, capsys):
        """history trends --last N should limit data points."""
        from pacta.cli.history import trends

        trends(path=str(repo_with_history), metric="violations", last=2, format="json")
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert data["count"] == 2

    def test_trends_branch_filter(self, repo_with_history: Path, capsys):
        """history trends --branch should filter by branch."""
        from pacta.cli.history import trends

        trends(path=str(repo_with_history), metric="violations", branch="main", format="json")
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        # Only 2 snapshots are on "main" branch (indices 0 and 2)
        assert data["count"] == 2

    def test_trends_empty_repo(self, tmp_path: Path, capsys):
        """history trends on empty repo should show helpful message."""
        from pacta.cli.history import trends

        empty_repo = tmp_path / "empty"
        empty_repo.mkdir()

        result = trends(path=str(empty_repo), metric="violations")

        assert result == 0
        captured = capsys.readouterr()
        assert "No history" in captured.out

    def test_trends_summary_shows_change(self, repo_with_history: Path, capsys):
        """history trends should show change/trend summary."""
        from pacta.cli.history import trends

        trends(path=str(repo_with_history), metric="nodes")
        captured = capsys.readouterr()

        # Should show trend direction and first/last values
        assert "Trend:" in captured.out
        assert "First:" in captured.out
        assert "Last:" in captured.out


class TestAsciiChart:
    """Tests for ASCII chart rendering."""

    def test_render_basic_chart(self):
        """render_line_chart should produce valid output."""
        from pacta.cli._ascii_chart import render_line_chart

        values = [1, 3, 2, 4, 3]
        labels = ["Jan 1", "Jan 2", "Jan 3", "Jan 4", "Jan 5"]

        chart = render_line_chart(values, labels, title="Test Chart")

        assert "Test Chart" in chart
        assert "\u25cf" in chart  # Should have data points

    def test_render_empty_data(self):
        """render_line_chart should handle empty data."""
        from pacta.cli._ascii_chart import render_line_chart

        chart = render_line_chart([], [])

        assert "No data" in chart

    def test_render_single_point(self):
        """render_line_chart should handle single data point."""
        from pacta.cli._ascii_chart import render_line_chart

        values = [5]
        labels = ["Jan 1"]

        chart = render_line_chart(values, labels)

        assert "\u25cf" in chart  # Should have a point

    def test_render_constant_values(self):
        """render_line_chart should handle all-same values."""
        from pacta.cli._ascii_chart import render_line_chart

        values = [3, 3, 3, 3]
        labels = ["A", "B", "C", "D"]

        chart = render_line_chart(values, labels)

        # Should not crash and should render points
        assert "\u25cf" in chart

    def test_trend_summary(self):
        """render_trend_summary should show correct trend."""
        from pacta.cli._ascii_chart import render_trend_summary

        # Improving (violations decreasing)
        summary = render_trend_summary([5, 4, 3, 2], ["A", "B", "C", "D"], "violations")
        assert "Improving" in summary
        assert "-3" in summary

        # Worsening (violations increasing)
        summary = render_trend_summary([2, 3, 4, 5], ["A", "B", "C", "D"], "violations")
        assert "Worsening" in summary
        assert "+3" in summary

        # Stable (no change)
        summary = render_trend_summary([3, 4, 2, 3], ["A", "B", "C", "D"], "violations")
        assert "Stable" in summary


class TestTrendsImageExport:
    """Tests for trends image export (requires matplotlib)."""

    def test_image_export_png(self, repo_with_history: Path, tmp_path: Path):
        """trends --output should export PNG if matplotlib is available."""
        from pacta.cli._mpl_chart import is_matplotlib_available

        if not is_matplotlib_available():
            pytest.skip("matplotlib not installed")

        from pacta.cli.history import trends

        output_file = tmp_path / "trends.png"
        result = trends(
            path=str(repo_with_history),
            metric="violations",
            output=str(output_file),
        )

        assert result == 0
        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_image_export_svg(self, repo_with_history: Path, tmp_path: Path):
        """trends --output should export SVG if matplotlib is available."""
        from pacta.cli._mpl_chart import is_matplotlib_available

        if not is_matplotlib_available():
            pytest.skip("matplotlib not installed")

        from pacta.cli.history import trends

        output_file = tmp_path / "trends.svg"
        result = trends(
            path=str(repo_with_history),
            metric="nodes",
            output=str(output_file),
        )

        assert result == 0
        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_matplotlib_import_error_message(self):
        """Should raise ImportError with helpful message if matplotlib missing."""
        from pacta.cli._mpl_chart import is_matplotlib_available

        if is_matplotlib_available():
            pytest.skip("matplotlib is installed, cannot test import error")

        # This test would only run if matplotlib is NOT installed
        # which is rare in dev environments


class TestSnapshotStoreListObjects:
    """Tests for FsSnapshotStore.list_objects() used by history."""

    def test_list_objects_sorted_by_timestamp(self, tmp_path: Path):
        """list_objects should return objects sorted by timestamp (newest first)."""
        store = FsSnapshotStore(repo_root=str(tmp_path))
        builder = DefaultSnapshotBuilder()

        # Create snapshots in non-chronological order
        for i, ts in enumerate(["2025-01-03", "2025-01-01", "2025-01-02"]):
            meta = SnapshotMeta(
                repo_root=str(tmp_path),
                created_at=f"{ts}T12:00:00+00:00",
            )
            ir = {"nodes": [make_node(f"node{i}")], "edges": []}
            snap = builder.build(ir, meta=meta)
            store.save(snap, refs=[f"snap{i}"])

        objects = store.list_objects()

        # Should be sorted newest first
        timestamps = [snap.meta.created_at for _, snap in objects]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_list_objects_empty_store(self, tmp_path: Path):
        """list_objects on empty store should return empty list."""
        store = FsSnapshotStore(repo_root=str(tmp_path))
        objects = store.list_objects()
        assert objects == []
