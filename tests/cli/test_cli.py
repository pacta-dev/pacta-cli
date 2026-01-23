"""Simple tests for Pacta CLI commands."""

from unittest.mock import patch

from pacta.cli.main import main
from pacta.reporting.types import EngineError, Report, RuleRef, RunInfo, Severity, Summary, Violation


def create_test_report(repo_root, violations=None, engine_errors=None, **overrides):
    """Helper to create a test Report with proper Summary."""
    violations = violations or []
    engine_errors = engine_errors or []

    # Build summary
    by_severity = {}
    by_status = {}
    by_rule = {}

    for v in violations:
        sev_key = v.rule.severity.value
        by_severity[sev_key] = by_severity.get(sev_key, 0) + 1

        status = v.status
        by_status[status] = by_status.get(status, 0) + 1

        rule_id = v.rule.id
        by_rule[rule_id] = by_rule.get(rule_id, 0) + 1

    summary = Summary(
        total_violations=len(violations),
        by_severity=by_severity,
        by_status=by_status,
        by_rule=by_rule,
        engine_errors=len(engine_errors),
    )

    return Report(
        tool="pacta",
        version="0.0.1",
        run=RunInfo(
            repo_root=str(repo_root),
            commit=None,
            branch=None,
            model_file=overrides.get("model_file"),
            rules_files=overrides.get("rules_files", ()),
            baseline_ref=overrides.get("baseline_ref"),
            mode=overrides.get("mode", "full"),
            created_at=None,
            tool_version="0.0.1",
            metadata={},
        ),
        summary=summary,
        violations=tuple(violations),
        engine_errors=tuple(engine_errors),
        diff=None,
    )


class TestCLIMain:
    """Tests for main CLI entry point and command routing."""

    def test_scan_command_with_text_format(self, tmp_path):
        """Test scan command with text output format."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        rules_file = repo_root / "pacta.rules"
        rules_file.write_text('rule "test" { when { true } then { pass() } }')

        mock_report = create_test_report(repo_root, rules_files=(str(rules_file),))

        with patch("pacta.cli.scan.run_engine_scan", return_value=mock_report):
            exit_code = main(["scan", str(repo_root), "--format", "text"])

        assert exit_code == 0

    def test_scan_command_with_json_format(self, tmp_path):
        """Test scan command with JSON output format."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        mock_report = create_test_report(repo_root)

        with patch("pacta.cli.scan.run_engine_scan", return_value=mock_report):
            exit_code = main(["scan", str(repo_root), "--format", "json"])

        assert exit_code == 0

    def test_scan_exit_code_1_on_new_violations(self, tmp_path):
        """Test that scan returns exit code 1 when new ERROR violations exist."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        violation = Violation(
            rule=RuleRef(
                id="test_rule",
                name="Test Rule",
                severity=Severity.ERROR,
            ),
            message="Test violation",
            location=None,
            status="new",
        )

        mock_report = create_test_report(repo_root, violations=[violation])

        with patch("pacta.cli.scan.run_engine_scan", return_value=mock_report):
            exit_code = main(["scan", str(repo_root)])

        assert exit_code == 1

    def test_scan_exit_code_2_on_engine_error(self, tmp_path):
        """Test that scan returns exit code 2 when engine errors occur."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        error = EngineError(
            type="runtime_error",
            message="Engine failed",
            location=None,
        )

        mock_report = create_test_report(repo_root, engine_errors=[error])

        with patch("pacta.cli.scan.run_engine_scan", return_value=mock_report):
            exit_code = main(["scan", str(repo_root)])

        assert exit_code == 2

    def test_scan_with_custom_rules_file(self, tmp_path):
        """Test scan command with custom rules file."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        custom_rules = tmp_path / "custom.rules"
        custom_rules.write_text('rule "custom" { when { true } then { pass() } }')

        mock_report = create_test_report(repo_root, rules_files=(str(custom_rules),))

        with patch("pacta.cli.scan.run_engine_scan", return_value=mock_report) as mock_scan:
            exit_code = main(["scan", str(repo_root), "--rules", str(custom_rules)])

        assert exit_code == 0
        # Verify the rules file was passed correctly
        call_kwargs = mock_scan.call_args.kwargs
        assert str(custom_rules) in call_kwargs["rules_files"]

    def test_scan_with_baseline(self, tmp_path):
        """Test scan command with baseline comparison."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        mock_report = create_test_report(repo_root, baseline_ref="baseline")

        with patch("pacta.cli.scan.run_engine_scan", return_value=mock_report) as mock_scan:
            exit_code = main(["scan", str(repo_root), "--baseline", "baseline"])

        assert exit_code == 0
        assert mock_scan.call_args.kwargs["baseline_ref"] == "baseline"


class TestSnapshotCommands:
    """Tests for snapshot-related CLI commands."""

    def test_snapshot_save_creates_file(self, tmp_path):
        """Test that snapshot save creates a snapshot file."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Mock the entire snapshot.save function
        with patch("pacta.cli.snapshot.save", return_value=0) as mock_save:
            exit_code = main(["snapshot", "save", str(repo_root), "--ref", "test"])

        assert exit_code == 0
        # Verify save was called with correct parameters
        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args.kwargs
        assert call_kwargs["path"] == str(repo_root)
        assert call_kwargs["ref"] == "test"

    def test_snapshot_save_with_custom_ref(self, tmp_path):
        """Test snapshot save with custom reference name."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        with patch("pacta.cli.snapshot.save", return_value=0) as mock_save:
            exit_code = main(["snapshot", "save", str(repo_root), "--ref", "my-snapshot"])

        assert exit_code == 0
        call_kwargs = mock_save.call_args.kwargs
        assert call_kwargs["ref"] == "my-snapshot"


class TestDiffCommand:
    """Tests for diff command."""

    def test_diff_between_snapshots(self, tmp_path):
        """Test diff command comparing two snapshots."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Mock the entire diff.snapshot_diff function
        with patch("pacta.cli.diff.snapshot_diff", return_value=0) as mock_diff:
            exit_code = main(["diff", str(repo_root), "--from", "snap1", "--to", "snap2"])

        assert exit_code == 0
        # Verify diff was called with correct parameters
        mock_diff.assert_called_once()
        call_kwargs = mock_diff.call_args.kwargs
        assert call_kwargs["path"] == str(repo_root)
        assert call_kwargs["from_ref"] == "snap1"
        assert call_kwargs["to_ref"] == "snap2"


class TestSaveRef:
    """Tests for --save-ref option on scan command."""

    def test_scan_with_save_ref(self, tmp_path):
        """Test scan command with --save-ref option."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        mock_report = create_test_report(repo_root)

        with patch("pacta.cli.scan.run_engine_scan", return_value=mock_report) as mock_scan:
            exit_code = main(["scan", str(repo_root), "--save-ref", "baseline"])

        assert exit_code == 0
        assert mock_scan.call_args.kwargs["save_ref"] == "baseline"

    def test_scan_with_custom_save_ref(self, tmp_path):
        """Test scan command with custom --save-ref value."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        mock_report = create_test_report(repo_root)

        with patch("pacta.cli.scan.run_engine_scan", return_value=mock_report) as mock_scan:
            exit_code = main(["scan", str(repo_root), "--save-ref", "my-baseline"])

        assert exit_code == 0
        assert mock_scan.call_args.kwargs["save_ref"] == "my-baseline"


class TestArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_scan_requires_no_positional_args(self):
        """Test that scan uses current directory by default."""
        with patch("pacta.cli.scan.run_engine_scan") as mock_scan:
            mock_report = create_test_report(".")
            mock_scan.return_value = mock_report

            exit_code = main(["scan"])

        assert exit_code == 0

    def test_multiple_rules_files(self, tmp_path):
        """Test scan with multiple rules files."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        rules1 = tmp_path / "rules1.pacta"
        rules2 = tmp_path / "rules2.pacta"
        rules1.write_text('rule "r1" { when { true } then { pass() } }')
        rules2.write_text('rule "r2" { when { true } then { pass() } }')

        mock_report = create_test_report(repo_root, rules_files=(str(rules1), str(rules2)))

        with patch("pacta.cli.scan.run_engine_scan", return_value=mock_report) as mock_scan:
            exit_code = main(
                [
                    "scan",
                    str(repo_root),
                    "--rules",
                    str(rules1),
                    "--rules",
                    str(rules2),
                ]
            )

        assert exit_code == 0
        rules_files = mock_scan.call_args.kwargs["rules_files"]
        assert str(rules1) in rules_files
        assert str(rules2) in rules_files

    def test_scan_mode_changed_only(self, tmp_path):
        """Test scan with changed_only mode."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        mock_report = create_test_report(repo_root, mode="changed_only")

        with patch("pacta.cli.scan.run_engine_scan", return_value=mock_report) as mock_scan:
            exit_code = main(["scan", str(repo_root), "--mode", "changed_only"])

        assert exit_code == 0
        assert mock_scan.call_args.kwargs["mode"] == "changed_only"


class TestErrorHandling:
    """Tests for CLI error handling."""

    def test_invalid_path_shows_error(self):
        """Test that invalid path shows appropriate error."""
        exit_code = main(["scan", "/nonexistent/path"])

        # Should return error exit code
        assert exit_code == 2

    def test_exception_returns_error_exit_code(self, tmp_path):
        """Test that exceptions are caught and return error exit code."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        with patch("pacta.cli.scan.run_engine_scan", side_effect=Exception("Test error")):
            exit_code = main(["scan", str(repo_root)])

        assert exit_code == 2
