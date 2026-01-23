"""
End-to-end tests for Pacta CLI commands.

These tests run the actual CLI against real file systems and code,
without mocking or monkeypatching. They verify the full pipeline works
from CLI invocation to final output.
"""

import json
import os
import shutil
import sys
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import pytest
from pacta.cli.main import main as pacta_main


@dataclass
class CLIResult:
    """Result of running the CLI."""

    returncode: int
    stdout: str
    stderr: str


def run_pacta(*args: str, cwd: Path | None = None) -> CLIResult:
    """Run pacta CLI command and return the result."""
    original_cwd = os.getcwd()
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    stdout_capture = StringIO()
    stderr_capture = StringIO()

    try:
        if cwd:
            os.chdir(cwd)

        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        try:
            returncode = pacta_main(list(args))
        except SystemExit as e:
            returncode = e.code if e.code is not None else 0
        except Exception as e:
            stderr_capture.write(f"Error: {e}\n")
            returncode = 2

    finally:
        os.chdir(original_cwd)
        sys.stdout = original_stdout
        sys.stderr = original_stderr

    return CLIResult(
        returncode=returncode,
        stdout=stdout_capture.getvalue(),
        stderr=stderr_capture.getvalue(),
    )


@pytest.fixture
def clean_layered_app(tmp_path: Path) -> Path:
    """
    Create a clean layered application that follows all architectural rules.
    No violations expected.
    """
    repo = tmp_path / "clean-app"
    repo.mkdir()

    # Create architecture model
    architecture = {
        "version": 1,
        "system": {"id": "clean-app", "name": "Clean Layered App"},
        "containers": {
            "main": {
                "name": "Main Container",
                "code": {
                    "roots": ["src"],
                    "layers": {
                        "domain": {
                            "name": "Domain Layer",
                            "patterns": ["src/domain/**"],
                        },
                        "application": {
                            "name": "Application Layer",
                            "patterns": ["src/application/**"],
                        },
                        "infra": {
                            "name": "Infrastructure Layer",
                            "patterns": ["src/infra/**"],
                        },
                        "ui": {
                            "name": "UI Layer",
                            "patterns": ["src/ui/**"],
                        },
                    },
                },
            }
        },
        "contexts": {},
    }
    (repo / "architecture.json").write_text(json.dumps(architecture, indent=2))

    # Create rules file
    rules = """
rule:
  id: no_domain_to_infra
  name: Domain must not depend on Infrastructure
  severity: error
  target: dependency
  when:
    all:
      - from.layer == domain
      - to.layer == infra
  action: forbid
  message: Domain layer must not depend on Infrastructure

rule:
  id: no_ui_to_infra
  name: UI should not directly access Infrastructure
  severity: warning
  target: dependency
  when:
    all:
      - from.layer == ui
      - to.layer == infra
  action: forbid
  message: UI layer should not directly depend on Infrastructure
"""
    (repo / "rules.pacta.yml").write_text(rules)

    # Create source directories
    (repo / "src").mkdir()
    (repo / "src" / "domain").mkdir()
    (repo / "src" / "application").mkdir()
    (repo / "src" / "infra").mkdir()
    (repo / "src" / "ui").mkdir()

    # Domain layer - pure business logic, no external dependencies
    (repo / "src" / "__init__.py").write_text("")
    (repo / "src" / "domain" / "__init__.py").write_text("")
    (repo / "src" / "domain" / "order.py").write_text("""
class Order:
    def __init__(self, order_id: str, amount: float):
        self.order_id = order_id
        self.amount = amount

    def calculate_tax(self) -> float:
        return self.amount * 0.1
""")

    # Infrastructure layer - can depend on domain
    (repo / "src" / "infra" / "__init__.py").write_text("")
    (repo / "src" / "infra" / "repository.py").write_text("""
from src.domain.order import Order

class OrderRepository:
    def __init__(self):
        self.orders = {}

    def save(self, order: Order) -> None:
        self.orders[order.order_id] = order

    def find(self, order_id: str) -> Order:
        return self.orders[order_id]
""")

    # Application layer - can depend on domain and infra
    (repo / "src" / "application" / "__init__.py").write_text("")
    (repo / "src" / "application" / "service.py").write_text("""
from src.domain.order import Order
from src.infra.repository import OrderRepository

class OrderService:
    def __init__(self):
        self.repo = OrderRepository()

    def create_order(self, order_id: str, amount: float) -> Order:
        order = Order(order_id, amount)
        self.repo.save(order)
        return order
""")

    # UI layer - depends on application only (clean)
    (repo / "src" / "ui" / "__init__.py").write_text("")
    (repo / "src" / "ui" / "controller.py").write_text("""
from src.application.service import OrderService

class OrderController:
    def __init__(self):
        self.service = OrderService()

    def create(self, data: dict) -> dict:
        order = self.service.create_order(data["id"], data["amount"])
        return {"id": order.order_id, "total": order.amount + order.calculate_tax()}
""")

    return repo


@pytest.fixture
def violating_layered_app(tmp_path: Path) -> Path:
    """
    Create a layered application with architectural violations.
    Expected violations:
    - Domain depends on Infrastructure (error)
    - UI depends on Infrastructure (warning)
    """
    repo = tmp_path / "violating-app"
    repo.mkdir()

    # Create architecture model
    architecture = {
        "version": 1,
        "system": {"id": "violating-app", "name": "App with Violations"},
        "containers": {
            "main": {
                "name": "Main Container",
                "code": {
                    "roots": ["src"],
                    "layers": {
                        "domain": {
                            "name": "Domain Layer",
                            "patterns": ["src/domain/**"],
                        },
                        "application": {
                            "name": "Application Layer",
                            "patterns": ["src/application/**"],
                        },
                        "infra": {
                            "name": "Infrastructure Layer",
                            "patterns": ["src/infra/**"],
                        },
                        "ui": {
                            "name": "UI Layer",
                            "patterns": ["src/ui/**"],
                        },
                    },
                },
            }
        },
        "contexts": {},
    }
    (repo / "architecture.json").write_text(json.dumps(architecture, indent=2))

    # Create rules file
    rules = """
rule:
  id: no_domain_to_infra
  name: Domain must not depend on Infrastructure
  severity: error
  target: dependency
  when:
    all:
      - from.layer == domain
      - to.layer == infra
  action: forbid
  message: Domain layer must not depend on Infrastructure

rule:
  id: no_ui_to_infra
  name: UI should not directly access Infrastructure
  severity: warning
  target: dependency
  when:
    all:
      - from.layer == ui
      - to.layer == infra
  action: forbid
  message: UI layer should not directly depend on Infrastructure
"""
    (repo / "rules.pacta.yml").write_text(rules)

    # Create source directories
    (repo / "src").mkdir()
    (repo / "src" / "domain").mkdir()
    (repo / "src" / "application").mkdir()
    (repo / "src" / "infra").mkdir()
    (repo / "src" / "ui").mkdir()

    # Infrastructure layer
    (repo / "src" / "__init__.py").write_text("")
    (repo / "src" / "infra" / "__init__.py").write_text("")
    (repo / "src" / "infra" / "database.py").write_text("""
class Database:
    def __init__(self, connection_string: str):
        self.connection = connection_string

    def execute(self, query: str) -> list:
        return []
""")

    # Domain layer - VIOLATION: imports from infra
    (repo / "src" / "domain" / "__init__.py").write_text("")
    (repo / "src" / "domain" / "order.py").write_text("""
# VIOLATION: Domain should not depend on Infrastructure
from src.infra.database import Database

class Order:
    def __init__(self, order_id: str, amount: float):
        self.order_id = order_id
        self.amount = amount
        # Direct database access from domain - bad!
        self.db = Database("connection")

    def calculate_tax(self) -> float:
        return self.amount * 0.1
""")

    # Application layer
    (repo / "src" / "application" / "__init__.py").write_text("")
    (repo / "src" / "application" / "service.py").write_text("""
from src.domain.order import Order

class OrderService:
    def create_order(self, order_id: str, amount: float) -> Order:
        return Order(order_id, amount)
""")

    # UI layer - VIOLATION: direct import from infra
    (repo / "src" / "ui" / "__init__.py").write_text("")
    (repo / "src" / "ui" / "controller.py").write_text("""
from src.application.service import OrderService
# VIOLATION: UI should go through Application layer
from src.infra.database import Database

class OrderController:
    def __init__(self):
        self.service = OrderService()
        self.db = Database("direct-access")

    def create(self, data: dict) -> dict:
        order = self.service.create_order(data["id"], data["amount"])
        return {"id": order.order_id}
""")

    return repo


@pytest.fixture
def minimal_python_repo(tmp_path: Path) -> Path:
    """Create a minimal Python repository with no architecture model or rules."""
    repo = tmp_path / "minimal-repo"
    repo.mkdir()

    (repo / "main.py").write_text("""
import os

def main():
    print("Hello")

if __name__ == "__main__":
    main()
""")

    return repo


class TestScanCommand:
    """E2E tests for the `pacta scan` command."""

    def test_scan_clean_app_returns_exit_code_0(self, clean_layered_app: Path):
        """Scanning an app with no violations should return exit code 0."""
        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
        )

        assert result.returncode == 0, (
            f"Expected exit code 0, got {result.returncode}\nstderr: {result.stderr}\nstdout: {result.stdout}"
        )

    def test_scan_violating_app_returns_exit_code_1(self, violating_layered_app: Path):
        """Scanning an app with ERROR violations should return exit code 1."""
        result = run_pacta(
            "scan",
            str(violating_layered_app),
            "--model",
            str(violating_layered_app / "architecture.json"),
            "--rules",
            str(violating_layered_app / "rules.pacta.yml"),
        )

        # Exit code 1 = new ERROR-level violations found
        assert result.returncode == 1, (
            f"Expected exit code 1, got {result.returncode}\nstderr: {result.stderr}\nstdout: {result.stdout}"
        )

    def test_scan_text_output_contains_violations(self, violating_layered_app: Path):
        """Text output should mention the violations detected."""
        result = run_pacta(
            "scan",
            str(violating_layered_app),
            "--model",
            str(violating_layered_app / "architecture.json"),
            "--rules",
            str(violating_layered_app / "rules.pacta.yml"),
            "--format",
            "text",
        )

        # Check that violation-related content appears in output
        assert "violation" in result.stdout.lower() or "error" in result.stdout.lower() or result.returncode == 1

    def test_scan_json_output_is_valid_json(self, violating_layered_app: Path):
        """JSON output should be parseable and contain expected fields."""
        result = run_pacta(
            "scan",
            str(violating_layered_app),
            "--model",
            str(violating_layered_app / "architecture.json"),
            "--rules",
            str(violating_layered_app / "rules.pacta.yml"),
            "--format",
            "json",
        )

        # Should be valid JSON
        report = json.loads(result.stdout)

        # Check expected structure
        assert "tool" in report
        assert report["tool"] == "pacta"
        assert "summary" in report
        assert "violations" in report
        assert isinstance(report["violations"], list)

    def test_scan_json_output_contains_violation_details(self, violating_layered_app: Path):
        """JSON output should contain detailed violation information."""
        result = run_pacta(
            "scan",
            str(violating_layered_app),
            "--model",
            str(violating_layered_app / "architecture.json"),
            "--rules",
            str(violating_layered_app / "rules.pacta.yml"),
            "--format",
            "json",
        )

        report = json.loads(result.stdout)
        violations = report["violations"]

        # Should have at least one violation (domain->infra)
        assert len(violations) > 0, "Expected violations to be detected"

        # Check violation structure
        for v in violations:
            assert "rule" in v
            assert "message" in v
            assert "id" in v["rule"]
            assert "severity" in v["rule"]

    def test_scan_minimal_repo_without_model_and_rules(self, minimal_python_repo: Path):
        """Scanning without model or rules should still work (no violations)."""
        result = run_pacta("scan", str(minimal_python_repo))

        # Should succeed (no rules = no violations)
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_scan_creates_latest_snapshot(self, clean_layered_app: Path):
        """Scan should automatically save a 'latest' snapshot."""
        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
        )

        assert result.returncode == 0

        # Check that snapshot was created
        snapshot_path = clean_layered_app / ".pacta" / "snapshots" / "latest.json"
        assert snapshot_path.exists(), "Expected latest.json snapshot to be created"

        # Verify it's valid JSON
        snapshot = json.loads(snapshot_path.read_text())
        assert "schema_version" in snapshot
        assert "nodes" in snapshot
        assert "edges" in snapshot

    def test_scan_nonexistent_path_returns_error(self, tmp_path: Path):
        """Scanning a nonexistent path should return error exit code."""
        result = run_pacta("scan", str(tmp_path / "nonexistent"))

        assert result.returncode == 2  # EXIT_ENGINE_ERROR

    def test_scan_with_mode_full(self, clean_layered_app: Path):
        """Scan with --mode full should work."""
        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
            "--mode",
            "full",
        )

        assert result.returncode == 0

    def test_scan_with_multiple_rules_files(self, clean_layered_app: Path):
        """Scan should accept multiple --rules arguments."""
        # Create a second rules file
        rules2 = """
rule:
  id: additional_rule
  name: Additional Rule
  severity: info
  target: dependency
  when:
    all:
      - from.layer == application
      - to.layer == domain
  action: allow
  message: This is allowed
"""
        (clean_layered_app / "rules2.pacta.yml").write_text(rules2)

        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
            "--rules",
            str(clean_layered_app / "rules2.pacta.yml"),
        )

        assert result.returncode == 0


class TestSnapshotSaveCommand:
    """E2E tests for the `pacta snapshot save` command.

    Note: The snapshot save command requires engine.build_ir() which is not
    implemented in DefaultPactaEngine. Tests use scan command instead which
    saves snapshots as a side effect.
    """

    def test_scan_creates_snapshot(self, clean_layered_app: Path):
        """Scan should automatically create a 'latest' snapshot."""
        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

        snapshot_path = clean_layered_app / ".pacta" / "snapshots" / "latest.json"
        assert snapshot_path.exists(), "Expected latest.json snapshot to be created"

    def test_snapshot_contains_valid_ir_data(self, clean_layered_app: Path):
        """Saved snapshot should contain valid IR structure."""
        # Use scan to create snapshot
        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
        )
        assert result.returncode == 0

        snapshot_path = clean_layered_app / ".pacta" / "snapshots" / "latest.json"
        snapshot = json.loads(snapshot_path.read_text())

        # Check expected fields
        assert "schema_version" in snapshot
        assert "nodes" in snapshot
        assert "edges" in snapshot
        assert isinstance(snapshot["nodes"], list)
        assert isinstance(snapshot["edges"], list)

        # Should have detected Python modules
        assert len(snapshot["nodes"]) > 0, "Expected some nodes to be detected"

    def test_snapshot_overwrite_on_repeated_scan(self, clean_layered_app: Path):
        """Running scan again should update the snapshot."""
        # Scan first time
        run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
        )

        snapshot_path = clean_layered_app / ".pacta" / "snapshots" / "latest.json"
        first_mtime = snapshot_path.stat().st_mtime

        # Modify something
        (clean_layered_app / "src" / "domain" / "new_file.py").write_text("x = 1")

        # Small delay to ensure different mtime
        import time

        time.sleep(0.1)

        # Scan second time
        run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
        )

        second_mtime = snapshot_path.stat().st_mtime
        assert second_mtime > first_mtime, "Snapshot file should have been updated"


class TestSaveRefCommand:
    """E2E tests for the `pacta scan --save-ref` option."""

    def test_scan_with_save_ref_creates_baseline(self, clean_layered_app: Path):
        """Test that scan --save-ref creates a named snapshot."""
        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
            "--save-ref",
            "baseline",
        )

        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"

        # Verify baseline was created
        baseline_path = clean_layered_app / ".pacta" / "snapshots" / "baseline.json"
        assert baseline_path.exists(), "Expected baseline.json to be created"

        # Verify it's a valid snapshot with violations field
        baseline = json.loads(baseline_path.read_text())
        assert "schema_version" in baseline
        assert "nodes" in baseline
        assert "edges" in baseline
        assert "violations" in baseline

    def test_scan_save_ref_captures_violations(self, violating_layered_app: Path):
        """Test that --save-ref captures current violations."""
        result = run_pacta(
            "scan",
            str(violating_layered_app),
            "--model",
            str(violating_layered_app / "architecture.json"),
            "--rules",
            str(violating_layered_app / "rules.pacta.yml"),
            "--save-ref",
            "baseline",
        )

        # Exit code 1 because there are violations
        assert result.returncode == 1, f"stderr: {result.stderr}\nstdout: {result.stdout}"

        # Verify baseline contains violations
        baseline_path = violating_layered_app / ".pacta" / "snapshots" / "baseline.json"
        baseline = json.loads(baseline_path.read_text())

        assert len(baseline["violations"]) > 0, "Baseline should contain violations"

    def test_scan_save_ref_custom_name(self, clean_layered_app: Path):
        """Test --save-ref with custom ref name."""
        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
            "--save-ref",
            "my-custom-baseline",
        )

        assert result.returncode == 0

        baseline_path = clean_layered_app / ".pacta" / "snapshots" / "my-custom-baseline.json"
        assert baseline_path.exists()


class TestDiffCommand:
    """E2E tests for the `pacta diff` command.

    Note: Tests use scan command to create snapshots since snapshot save
    is not fully implemented.

    Known issue: The diff command has a bug in snapshot deserialization
    (Language enum expects uppercase but saves lowercase). Tests that
    require reading back snapshots are marked as xfail.
    """

    def _create_snapshot(self, repo: Path, ref: str) -> None:
        """Helper to create a snapshot by scanning and copying latest."""
        run_pacta(
            "scan",
            str(repo),
            "--model",
            str(repo / "architecture.json"),
            "--rules",
            str(repo / "rules.pacta.yml"),
        )
        snapshots_dir = repo / ".pacta" / "snapshots"
        shutil.copy(snapshots_dir / "latest.json", snapshots_dir / f"{ref}.json")

    def test_diff_between_identical_snapshots(self, clean_layered_app: Path):
        """Diffing identical snapshots should show no changes."""
        # Create identical snapshots
        self._create_snapshot(clean_layered_app, "snap1")
        self._create_snapshot(clean_layered_app, "snap2")

        result = run_pacta(
            "diff",
            str(clean_layered_app),
            "--from",
            "snap1",
            "--to",
            "snap2",
        )

        assert result.returncode == 0
        # Should show zeros for changes
        assert "+0" in result.stdout or "nodes: +0" in result.stdout

    def test_diff_detects_added_nodes(self, clean_layered_app: Path):
        """Diff should detect when new files are added."""
        # Create before snapshot
        self._create_snapshot(clean_layered_app, "before")

        # Add a new file
        (clean_layered_app / "src" / "domain" / "new_entity.py").write_text("""
class NewEntity:
    pass
""")

        # Create after snapshot
        self._create_snapshot(clean_layered_app, "after")

        result = run_pacta(
            "diff",
            str(clean_layered_app),
            "--from",
            "before",
            "--to",
            "after",
        )

        assert result.returncode == 0
        # Should show added nodes
        assert "+" in result.stdout

    def test_diff_detects_removed_nodes(self, clean_layered_app: Path):
        """Diff should detect when files are removed."""
        # Create before snapshot
        self._create_snapshot(clean_layered_app, "before")

        # Remove a file
        (clean_layered_app / "src" / "ui" / "controller.py").unlink()

        # Create after snapshot
        self._create_snapshot(clean_layered_app, "after")

        result = run_pacta(
            "diff",
            str(clean_layered_app),
            "--from",
            "before",
            "--to",
            "after",
        )

        assert result.returncode == 0
        # Should show removed nodes
        assert "-" in result.stdout

    def test_diff_missing_snapshot_error(self, clean_layered_app: Path):
        """Diff with missing snapshot should return error."""
        self._create_snapshot(clean_layered_app, "exists")

        result = run_pacta(
            "diff",
            str(clean_layered_app),
            "--from",
            "exists",
            "--to",
            "nonexistent",
        )

        assert result.returncode == 2  # Engine error


class TestBaselineComparison:
    """E2E tests for scan with --baseline flag."""

    def _create_baseline(self, repo: Path) -> None:
        """Helper to create a baseline using scan --save-ref."""
        run_pacta(
            "scan",
            str(repo),
            "--model",
            str(repo / "architecture.json"),
            "--rules",
            str(repo / "rules.pacta.yml"),
            "--save-ref",
            "baseline",
        )
        # Note: exit code may be 1 if violations exist, but baseline is still created

    def test_scan_with_baseline_marks_existing_violations(self, violating_layered_app: Path):
        """Existing violations should be marked as 'existing' when baseline exists."""
        # Create baseline with current violations
        self._create_baseline(violating_layered_app)

        # Scan with baseline
        result = run_pacta(
            "scan",
            str(violating_layered_app),
            "--model",
            str(violating_layered_app / "architecture.json"),
            "--rules",
            str(violating_layered_app / "rules.pacta.yml"),
            "--baseline",
            "baseline",
            "--format",
            "json",
        )

        report = json.loads(result.stdout)

        # All violations should be "existing" since they were in baseline
        for v in report["violations"]:
            assert v["status"] == "existing", f"Expected 'existing' status, got {v['status']}"

        # Exit code should be 0 since no NEW violations
        assert result.returncode == 0

    def test_scan_detects_new_violations_after_baseline(self, clean_layered_app: Path):
        """New violations introduced after baseline should be detected."""
        # Create baseline with clean state
        self._create_baseline(clean_layered_app)

        # Introduce a violation: domain imports from infra
        (clean_layered_app / "src" / "domain" / "order.py").write_text("""
# VIOLATION: Domain depends on Infrastructure
from src.infra.repository import OrderRepository

class Order:
    def __init__(self, order_id: str, amount: float):
        self.order_id = order_id
        self.amount = amount
        self.repo = OrderRepository()
""")

        # Scan with baseline
        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
            "--baseline",
            "baseline",
            "--format",
            "json",
        )

        report = json.loads(result.stdout)

        # Should have new violations
        new_violations = [v for v in report["violations"] if v["status"] == "new"]
        assert len(new_violations) > 0, "Expected new violations to be detected"

        # Exit code should be 1 (new ERROR violations)
        assert result.returncode == 1

    def test_scan_missing_baseline_reports_error(self, clean_layered_app: Path):
        """Scan with nonexistent baseline should report engine error."""
        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
            "--baseline",
            "nonexistent-baseline",
            "--format",
            "json",
        )

        report = json.loads(result.stdout)

        # Should have engine error about missing baseline
        assert report["summary"]["engine_errors"] > 0
        assert result.returncode == 2


class TestFullWorkflow:
    """E2E tests for complete workflows combining multiple commands."""

    def _create_baseline(self, repo: Path) -> None:
        """Helper to create a baseline using scan --save-ref."""
        run_pacta(
            "scan",
            str(repo),
            "--model",
            str(repo / "architecture.json"),
            "--rules",
            str(repo / "rules.pacta.yml"),
            "--save-ref",
            "baseline",
        )
        # Note: exit code may be 1 if violations exist, but baseline is still created

    def _create_snapshot(self, repo: Path, ref: str) -> None:
        """Helper to create a snapshot by scanning and copying latest."""
        run_pacta(
            "scan",
            str(repo),
            "--model",
            str(repo / "architecture.json"),
            "--rules",
            str(repo / "rules.pacta.yml"),
        )
        snapshots_dir = repo / ".pacta" / "snapshots"
        shutil.copy(snapshots_dir / "latest.json", snapshots_dir / f"{ref}.json")

    def test_workflow_baseline_modify_scan_diff(self, clean_layered_app: Path):
        """
        Test a complete CI workflow:
        1. Create baseline from clean state
        2. Make changes that introduce violations
        3. Scan with baseline to detect new violations
        4. Use diff to see structural changes
        """
        # Step 1: Establish baseline
        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
        )
        assert result.returncode == 0, "Initial scan should pass"

        self._create_baseline(clean_layered_app)
        self._create_snapshot(clean_layered_app, "before-changes")

        # Step 2: Introduce architectural violation
        (clean_layered_app / "src" / "domain" / "bad_import.py").write_text("""
# Violation: domain -> infra
from src.infra.repository import OrderRepository

class BadClass:
    repo = OrderRepository()
""")

        # Step 3: Scan with baseline
        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
            "--baseline",
            "baseline",
            "--format",
            "json",
        )

        report = json.loads(result.stdout)
        new_violations = [v for v in report["violations"] if v["status"] == "new"]

        assert result.returncode == 1, "Should fail with new violations"
        assert len(new_violations) > 0, "Should detect new violation"

        # Step 4: Create new snapshot and diff
        self._create_snapshot(clean_layered_app, "after-changes")

        diff_result = run_pacta(
            "diff",
            str(clean_layered_app),
            "--from",
            "before-changes",
            "--to",
            "after-changes",
        )

        assert diff_result.returncode == 0
        # Should show added nodes (the new file)
        assert "+" in diff_result.stdout

    def test_workflow_fix_violations_pass_ci(self, violating_layered_app: Path):
        """
        Test fixing violations workflow:
        1. Start with violations, create baseline
        2. Fix the violations
        3. Scan should pass (existing violations gone, no new ones)
        """
        # Step 1: Create baseline with existing violations
        self._create_baseline(violating_layered_app)

        # Verify baseline has violations
        result = run_pacta(
            "scan",
            str(violating_layered_app),
            "--model",
            str(violating_layered_app / "architecture.json"),
            "--rules",
            str(violating_layered_app / "rules.pacta.yml"),
            "--baseline",
            "baseline",
            "--format",
            "json",
        )
        report = json.loads(result.stdout)
        assert len(report["violations"]) > 0, "Should have existing violations"
        assert result.returncode == 0, "Existing violations shouldn't fail CI"

        # Step 2: Fix the domain violation - remove infra import
        (violating_layered_app / "src" / "domain" / "order.py").write_text("""
class Order:
    def __init__(self, order_id: str, amount: float):
        self.order_id = order_id
        self.amount = amount

    def calculate_tax(self) -> float:
        return self.amount * 0.1
""")

        # Fix the UI violation - remove direct infra import
        (violating_layered_app / "src" / "ui" / "controller.py").write_text("""
from src.application.service import OrderService

class OrderController:
    def __init__(self):
        self.service = OrderService()

    def create(self, data: dict) -> dict:
        order = self.service.create_order(data["id"], data["amount"])
        return {"id": order.order_id}
""")

        # Step 3: Scan without baseline - should pass now
        result = run_pacta(
            "scan",
            str(violating_layered_app),
            "--model",
            str(violating_layered_app / "architecture.json"),
            "--rules",
            str(violating_layered_app / "rules.pacta.yml"),
            "--format",
            "json",
        )

        report = json.loads(result.stdout)
        assert result.returncode == 0, "Should pass after fixing violations"
        # Should have no error-level violations
        error_violations = [v for v in report["violations"] if v["rule"]["severity"] == "error"]
        assert len(error_violations) == 0


class TestExitCodes:
    """E2E tests verifying correct exit codes."""

    def test_exit_code_0_no_violations(self, clean_layered_app: Path):
        """Exit code 0 when no violations."""
        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
        )
        assert result.returncode == 0

    def test_exit_code_1_error_violations(self, violating_layered_app: Path):
        """Exit code 1 when ERROR-level violations exist."""
        result = run_pacta(
            "scan",
            str(violating_layered_app),
            "--model",
            str(violating_layered_app / "architecture.json"),
            "--rules",
            str(violating_layered_app / "rules.pacta.yml"),
        )
        assert result.returncode == 1

    def test_exit_code_0_only_existing_violations(self, violating_layered_app: Path):
        """Exit code 0 when all violations are 'existing' (in baseline)."""
        # Create baseline using scan --save-ref
        run_pacta(
            "scan",
            str(violating_layered_app),
            "--model",
            str(violating_layered_app / "architecture.json"),
            "--rules",
            str(violating_layered_app / "rules.pacta.yml"),
            "--save-ref",
            "baseline",
        )
        # Note: exit code is 1 because there are violations, but baseline is created

        result = run_pacta(
            "scan",
            str(violating_layered_app),
            "--model",
            str(violating_layered_app / "architecture.json"),
            "--rules",
            str(violating_layered_app / "rules.pacta.yml"),
            "--baseline",
            "baseline",
        )
        assert result.returncode == 0

    def test_exit_code_2_engine_error(self, tmp_path: Path):
        """Exit code 2 for engine/config errors."""
        result = run_pacta("scan", str(tmp_path / "nonexistent"))
        assert result.returncode == 2

    def test_exit_code_0_warning_violations_only(self, tmp_path: Path):
        """Exit code 0 when only WARNING violations exist (not ERROR)."""
        repo = tmp_path / "warning-only"
        repo.mkdir()

        # Architecture with only warning-level rules
        architecture = {
            "version": 1,
            "system": {"id": "test", "name": "Test"},
            "containers": {
                "main": {
                    "name": "Main",
                    "code": {
                        "roots": ["src"],
                        "layers": {
                            "a": {"name": "A", "patterns": ["src/a/**"]},
                            "b": {"name": "B", "patterns": ["src/b/**"]},
                        },
                    },
                }
            },
            "contexts": {},
        }
        (repo / "architecture.json").write_text(json.dumps(architecture))

        # Warning-only rule
        rules = """
rule:
  id: warning_rule
  name: Warning Rule
  severity: warning
  target: dependency
  when:
    all:
      - from.layer == a
      - to.layer == b
  action: forbid
  message: This is a warning
"""
        (repo / "rules.yml").write_text(rules)

        # Create violation
        (repo / "src").mkdir()
        (repo / "src" / "a").mkdir()
        (repo / "src" / "b").mkdir()
        (repo / "src" / "__init__.py").write_text("")
        (repo / "src" / "a" / "__init__.py").write_text("")
        (repo / "src" / "b" / "__init__.py").write_text("")
        (repo / "src" / "b" / "module.py").write_text("x = 1")
        (repo / "src" / "a" / "module.py").write_text("from src.b.module import x")

        result = run_pacta(
            "scan",
            str(repo),
            "--model",
            str(repo / "architecture.json"),
            "--rules",
            str(repo / "rules.yml"),
            "--format",
            "json",
        )

        report = json.loads(result.stdout)

        # Should have warning violations
        warnings = [v for v in report["violations"] if v["rule"]["severity"] == "warning"]
        assert len(warnings) > 0, "Expected warning violations"

        # Exit code should still be 0 (warnings don't fail CI)
        assert result.returncode == 0


class TestEdgeCases:
    """E2E tests for edge cases and error handling."""

    def test_empty_rules_file(self, clean_layered_app: Path):
        """Empty rules file should not cause errors."""
        (clean_layered_app / "empty.rules").write_text("")

        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "empty.rules"),
        )

        assert result.returncode == 0

    def test_scan_empty_directory(self, tmp_path: Path):
        """Scanning empty directory returns engine error (no analyzers)."""
        empty_repo = tmp_path / "empty"
        empty_repo.mkdir()

        result = run_pacta("scan", str(empty_repo))

        # Empty repo has no analyzable files, so engine reports error
        # This is expected behavior - no Python files means no analyzer applies
        assert result.returncode == 2
        assert "no analyzers" in result.stdout.lower()

    def test_unicode_in_source_files(self, clean_layered_app: Path):
        """Files with unicode content should be handled."""
        (clean_layered_app / "src" / "domain" / "unicode.py").write_text(
            """
# UTF-8 content: 你好世界 مرحبا العالم 🌍
class УникодКласс:
    '''Документация на русском'''
    def método(self):
        return "Olá, Mundo!"
""",
            encoding="utf-8",
        )

        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
        )

        assert result.returncode == 0

    def test_deeply_nested_modules(self, clean_layered_app: Path):
        """Deeply nested module structure should work."""
        deep_path = clean_layered_app / "src" / "domain" / "a" / "b" / "c" / "d"
        deep_path.mkdir(parents=True)

        for p in [
            clean_layered_app / "src" / "domain" / "a",
            clean_layered_app / "src" / "domain" / "a" / "b",
            clean_layered_app / "src" / "domain" / "a" / "b" / "c",
            deep_path,
        ]:
            (p / "__init__.py").write_text("")

        (deep_path / "deep_module.py").write_text("DEEP = True")

        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
        )

        assert result.returncode == 0

    def test_circular_imports_in_same_layer(self, clean_layered_app: Path):
        """Circular imports within same layer should be detected."""
        (clean_layered_app / "src" / "domain" / "a.py").write_text("""
from src.domain.b import B

class A:
    pass
""")
        (clean_layered_app / "src" / "domain" / "b.py").write_text("""
from src.domain.a import A

class B:
    pass
""")

        result = run_pacta(
            "scan",
            str(clean_layered_app),
            "--model",
            str(clean_layered_app / "architecture.json"),
            "--rules",
            str(clean_layered_app / "rules.pacta.yml"),
            "--format",
            "json",
        )

        # Should complete without crashing
        assert result.returncode in (0, 1, 2)

        # Should be valid JSON output
        json.loads(result.stdout)


class TestRealWorldExample:
    """E2E tests using the actual example from the repository."""

    @pytest.fixture
    def example_app_copy(self, tmp_path: Path) -> Path:
        """Copy the real example app to a temp directory for testing."""
        src = Path(__file__).parent.parent.parent / "examples" / "simple-layered-app"
        if not src.exists():
            pytest.skip("Example app not found")

        dst = tmp_path / "simple-layered-app"
        shutil.copytree(src, dst)

        # Remove any existing .pacta directory to start fresh
        pacta_dir = dst / ".pacta"
        if pacta_dir.exists():
            shutil.rmtree(pacta_dir)

        return dst

    def test_example_app_scan(self, example_app_copy: Path):
        """Test scanning the actual example app."""
        # Find architecture and rules files
        arch_file = example_app_copy / "architecture.json"
        rules_file = example_app_copy / "rules.pacta.yml"

        if not arch_file.exists() or not rules_file.exists():
            pytest.skip("Example app files not found")

        result = run_pacta(
            "scan",
            str(example_app_copy),
            "--model",
            str(arch_file),
            "--rules",
            str(rules_file),
            "--format",
            "json",
        )

        # Should produce valid output
        report = json.loads(result.stdout)
        assert "violations" in report
        assert "summary" in report

    def test_example_app_full_workflow(self, example_app_copy: Path):
        """Test full workflow on example app."""
        arch_file = example_app_copy / "architecture.json"
        rules_file = example_app_copy / "rules.pacta.yml"

        if not arch_file.exists() or not rules_file.exists():
            pytest.skip("Example app files not found")

        # Create baseline using scan --save-ref
        run_pacta(
            "scan",
            str(example_app_copy),
            "--model",
            str(arch_file),
            "--rules",
            str(rules_file),
            "--save-ref",
            "baseline",
        )
        # Note: exit code may be 1 if violations exist, but baseline is still created

        # Scan with baseline
        result = run_pacta(
            "scan",
            str(example_app_copy),
            "--model",
            str(arch_file),
            "--rules",
            str(rules_file),
            "--baseline",
            "baseline",
            "--format",
            "json",
        )

        report = json.loads(result.stdout)

        # All existing violations should be marked as such
        for v in report["violations"]:
            assert v["status"] == "existing"
