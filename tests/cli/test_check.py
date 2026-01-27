from unittest.mock import patch

from pacta.cli.main import main
from pacta.core.engine import CheckResult
from pacta.reporting.types import Report, RuleRef, RunInfo, Severity, Summary, Violation
from pacta.snapshot.types import Snapshot, SnapshotMeta


def _empty_snapshot(repo_root: str) -> Snapshot:
    return Snapshot(
        schema_version=1,
        meta=SnapshotMeta(repo_root=repo_root, commit="abc123", branch="main"),
        nodes=(),
        edges=(),
        violations=(),
    )


def _make_report(repo_root: str, violations=None, engine_errors=None) -> Report:
    violations = violations or []
    engine_errors = engine_errors or []

    by_severity = {}
    by_status = {}
    by_rule = {}
    for v in violations:
        sev_key = v.rule.severity.value
        by_severity[sev_key] = by_severity.get(sev_key, 0) + 1
        by_status[v.status] = by_status.get(v.status, 0) + 1
        by_rule[v.rule.id] = by_rule.get(v.rule.id, 0) + 1

    return Report(
        tool="pacta",
        version="0.0.4",
        run=RunInfo(
            repo_root=repo_root,
            commit=None,
            branch=None,
            model_file=None,
            rules_files=(),
            baseline_ref=None,
            mode="full",
            created_at=None,
            tool_version="0.0.4",
            metadata={},
        ),
        summary=Summary(
            total_violations=len(violations),
            by_severity=by_severity,
            by_status=by_status,
            by_rule=by_rule,
            engine_errors=len(engine_errors),
        ),
        violations=tuple(violations),
        engine_errors=tuple(engine_errors),
        diff=None,
    )


class TestCheckCommand:
    """Tests for the check CLI command."""

    def test_check_parser_accepts_valid_args(self, tmp_path):
        """Test that check command parses arguments correctly."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        snapshot = _empty_snapshot(str(repo_root))
        report = _make_report(str(repo_root))
        check_result = CheckResult(snapshot=snapshot, report=report, diff=None)

        with (
            patch("pacta.cli.check.FsSnapshotStore") as mock_store_cls,
            patch("pacta.cli.check.DefaultPactaEngine") as mock_engine_cls,
        ):
            store = mock_store_cls.return_value
            store.exists.return_value = True
            store.load.return_value = snapshot
            mock_engine_cls.return_value.check.return_value = check_result

            exit_code = main(["check", str(repo_root)])

        assert exit_code == 0

    def test_check_with_custom_ref(self, tmp_path):
        """Test check command with --ref flag."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        snapshot = _empty_snapshot(str(repo_root))
        report = _make_report(str(repo_root))
        check_result = CheckResult(snapshot=snapshot, report=report, diff=None)

        with (
            patch("pacta.cli.check.FsSnapshotStore") as mock_store_cls,
            patch("pacta.cli.check.DefaultPactaEngine") as mock_engine_cls,
        ):
            store = mock_store_cls.return_value
            store.exists.return_value = True
            store.load.return_value = snapshot
            mock_engine_cls.return_value.check.return_value = check_result

            exit_code = main(["check", str(repo_root), "--ref", "baseline"])

        assert exit_code == 0
        store.load.assert_called_once_with("baseline")

    def test_check_missing_snapshot_returns_error(self, tmp_path):
        """Test that check returns error when snapshot ref doesn't exist."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        with patch("pacta.cli.check.FsSnapshotStore") as mock_store_cls:
            store = mock_store_cls.return_value
            store.exists.return_value = False

            exit_code = main(["check", str(repo_root), "--ref", "nonexistent"])

        assert exit_code == 2

    def test_check_with_violations_returns_exit_code_1(self, tmp_path):
        """Test that check returns exit code 1 when violations are found."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        snapshot = _empty_snapshot(str(repo_root))
        violation = Violation(
            rule=RuleRef(id="test", name="Test", severity=Severity.ERROR),
            message="bad import",
            location=None,
            status="new",
        )
        report = _make_report(str(repo_root), violations=[violation])
        check_result = CheckResult(snapshot=snapshot, report=report, diff=None)

        with (
            patch("pacta.cli.check.FsSnapshotStore") as mock_store_cls,
            patch("pacta.cli.check.DefaultPactaEngine") as mock_engine_cls,
        ):
            store = mock_store_cls.return_value
            store.exists.return_value = True
            store.load.return_value = snapshot
            mock_engine_cls.return_value.check.return_value = check_result

            exit_code = main(["check", str(repo_root)])

        assert exit_code == 1

    def test_check_updates_existing_snapshot(self, tmp_path):
        """Test that check updates the existing snapshot object in-place."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        snapshot = _empty_snapshot(str(repo_root))
        report = _make_report(str(repo_root))
        check_result = CheckResult(snapshot=snapshot, report=report, diff=None)

        with (
            patch("pacta.cli.check.FsSnapshotStore") as mock_store_cls,
            patch("pacta.cli.check.DefaultPactaEngine") as mock_engine_cls,
        ):
            store = mock_store_cls.return_value
            store.exists.return_value = True
            store.load.return_value = snapshot
            store.resolve_ref.return_value = "abcd1234"
            mock_engine_cls.return_value.check.return_value = check_result

            main(["check", str(repo_root), "--ref", "myref"])

        store.update_object.assert_called_once_with("abcd1234", check_result.snapshot)

    def test_check_with_save_ref_creates_additional_ref(self, tmp_path):
        """Test that --save-ref saves under an additional ref."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        snapshot = _empty_snapshot(str(repo_root))
        report = _make_report(str(repo_root))
        check_result = CheckResult(snapshot=snapshot, report=report, diff=None)

        with (
            patch("pacta.cli.check.FsSnapshotStore") as mock_store_cls,
            patch("pacta.cli.check.DefaultPactaEngine") as mock_engine_cls,
        ):
            store = mock_store_cls.return_value
            store.exists.return_value = True
            store.load.return_value = snapshot
            store.resolve_ref.return_value = "abcd1234"
            mock_engine_cls.return_value.check.return_value = check_result

            main(["check", str(repo_root), "--ref", "myref", "--save-ref", "extra"])

        store.update_object.assert_called_once()
        store.save.assert_called_once()
        assert "extra" in store.save.call_args.kwargs.get(
            "refs", store.save.call_args[1] if len(store.save.call_args) > 1 else []
        )

    def test_check_json_format(self, tmp_path):
        """Test check command with JSON output."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        snapshot = _empty_snapshot(str(repo_root))
        report = _make_report(str(repo_root))
        check_result = CheckResult(snapshot=snapshot, report=report, diff=None)

        with (
            patch("pacta.cli.check.FsSnapshotStore") as mock_store_cls,
            patch("pacta.cli.check.DefaultPactaEngine") as mock_engine_cls,
        ):
            store = mock_store_cls.return_value
            store.exists.return_value = True
            store.load.return_value = snapshot
            mock_engine_cls.return_value.check.return_value = check_result

            exit_code = main(["check", str(repo_root), "--format", "json"])

        assert exit_code == 0
