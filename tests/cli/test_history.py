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
