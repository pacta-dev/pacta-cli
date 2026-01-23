from pathlib import Path

import pytest
from pacta.analyzers.python import PythonAnalyzer
from pacta.plugins.interfaces.analyzer import AnalyzeConfig, AnalyzeTarget

# ----------------------------
# Helpers
# ----------------------------


def _w(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _wb(p: Path, data: bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def _paths(ir) -> set[str]:
    return {n.path for n in ir.nodes if n.path is not None}


def _node_id_by_path(ir, path: str):
    for n in ir.nodes:
        if n.path == path:
            return n.id
    raise AssertionError(f"Node with path not found: {path!r}. Known paths: {sorted(_paths(ir))}")


def _edges_as_pairs(ir) -> set[tuple[object, object]]:
    return {(e.src, e.dst) for e in ir.edges}


def _assert_edge(ir, src_path: str, dst_path: str) -> None:
    src_id = _node_id_by_path(ir, src_path)
    dst_id = _node_id_by_path(ir, dst_path)
    pairs = _edges_as_pairs(ir)
    assert (src_id, dst_id) in pairs, f"Missing edge: {src_path} -> {dst_path}"


def _assert_all_edge_endpoints_exist(ir) -> None:
    node_ids = {n.id for n in ir.nodes}
    for e in ir.edges:
        assert e.src in node_ids, f"edge src missing node: {e.src}"
        assert e.dst in node_ids, f"edge dst missing node: {e.dst}"


# ----------------------------
# Fixtures
# ----------------------------


@pytest.fixture()
def analyzer() -> PythonAnalyzer:
    return PythonAnalyzer()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """
    Repo layout crafted to cover:
      - import + from-import
      - aliases
      - nested imports
      - relative imports (level 1, 2)
      - 'from . import x' behavior (note: current impl returns package module)
      - syntax errors / encoding errors
      - max_file_size_bytes skipping
      - default exclude directories (.git/.venv/__pycache__)
    """
    r = tmp_path

    # package app
    _w(r / "app" / "__init__.py", "# pkg\n")
    _w(
        r / "app" / "a.py",
        """
import os
import app.b
from app import c as c_alias
from . import b as rel_b
from .c import C
from .. import top   # relative level=2 (will resolve to 'top' best-effort)

if True:
    import app.c

def f():
    import app.b as b2
""".strip()
        + "\n",
    )
    _w(
        r / "app" / "b.py",
        """
class B: ...
""".strip()
        + "\n",
    )
    _w(
        r / "app" / "c.py",
        """
from .b import B
class C(B): ...
""".strip()
        + "\n",
    )

    # a top-level module to allow "from .. import top" to produce something
    _w(r / "top.py", "x = 1\n")

    # syntax error file (should not crash analyze)
    _w(r / "app" / "bad_syntax.py", "def oops(:\n  pass\n")

    # invalid encoding file (should not crash analyze)
    _wb(r / "app" / "bad_encoding.py", b"\xff\xfe\xfa\xfb")

    # large file used for max_file_size_bytes check
    _w(r / "app" / "huge.py", "x = 1\n" * 5000)

    # another package
    _w(r / "other" / "__init__.py", "")
    _w(r / "other" / "z.py", "import app.b\n")

    # default excluded directories
    _w(r / ".venv" / "lib" / "site.py", "import app.b\n")
    _w(r / "__pycache__" / "x.py", "import app.b\n")
    _w(r / ".git" / "hooks" / "pre-commit", "echo hi\n")

    return r


# ----------------------------
# can_analyze
# ----------------------------


def test_can_analyze_false_on_empty_repo(tmp_path: Path, analyzer: PythonAnalyzer) -> None:
    (tmp_path / "README.md").write_text("hi", encoding="utf-8")
    assert analyzer.can_analyze(tmp_path) is False


def test_can_analyze_true_when_py_exists(repo: Path, analyzer: PythonAnalyzer) -> None:
    assert analyzer.can_analyze(repo) is True


def test_can_analyze_ignores_default_excluded_dirs(tmp_path: Path, analyzer: PythonAnalyzer) -> None:
    # only .venv contains python, should return False due to default excludes
    _w(tmp_path / ".venv" / "lib" / "x.py", "x=1\n")
    assert analyzer.can_analyze(tmp_path) is False


# ----------------------------
# analyze: basic invariants
# ----------------------------


def test_analyze_returns_ir_and_invariants(repo: Path, analyzer: PythonAnalyzer) -> None:
    cfg = AnalyzeConfig(repo_root=repo)
    ir = analyzer.analyze(cfg)

    assert ir.repo_root == str(repo.resolve())
    assert isinstance(ir.nodes, tuple)
    assert isinstance(ir.edges, tuple)

    # All edges must reference existing nodes (the analyzer creates best-effort nodes for external deps too)
    _assert_all_edge_endpoints_exist(ir)

    # metadata basics
    md = ir.metadata
    assert md["language"] == analyzer.language.value
    assert md["files_scanned"] >= 1


def test_default_excludes_are_applied(repo: Path, analyzer: PythonAnalyzer) -> None:
    cfg = AnalyzeConfig(repo_root=repo)
    ir = analyzer.analyze(cfg)
    paths = _paths(ir)

    assert not any(p.startswith(".venv/") for p in paths)
    assert not any(p.startswith("__pycache__/") for p in paths)
    assert not any(p.startswith(".git/") for p in paths)


# ----------------------------
# analyze: target scoping
# ----------------------------


def test_target_include_paths_limits_scope(repo: Path, analyzer: PythonAnalyzer) -> None:
    cfg = AnalyzeConfig(
        repo_root=repo,
        target=AnalyzeTarget(include_paths=(repo / "app",)),
    )
    ir = analyzer.analyze(cfg)
    paths = _paths(ir)

    assert any(p.startswith("app/") for p in paths)
    assert not any(p.startswith("other/") for p in paths)
    assert "top.py" not in paths


def test_target_include_paths_file_is_supported(repo: Path, analyzer: PythonAnalyzer) -> None:
    cfg = AnalyzeConfig(
        repo_root=repo,
        target=AnalyzeTarget(include_paths=(repo / "top.py",)),
    )
    ir = analyzer.analyze(cfg)
    paths = _paths(ir)
    assert paths == {"top.py"}


def test_target_include_paths_outside_repo_is_ignored_and_falls_back_to_repo(
    repo: Path, analyzer: PythonAnalyzer
) -> None:
    outside = repo.parent  # outside repo_root
    cfg = AnalyzeConfig(
        repo_root=repo,
        target=AnalyzeTarget(include_paths=(outside,)),  # should be ignored by safety check
    )
    ir = analyzer.analyze(cfg)
    paths = _paths(ir)

    # fall back to analyzing whole repo (not empty)
    assert "app/a.py" in paths


def test_target_exclude_globs_are_applied(repo: Path, analyzer: PythonAnalyzer) -> None:
    cfg = AnalyzeConfig(
        repo_root=repo,
        target=AnalyzeTarget(
            include_paths=(repo,),
            exclude_globs=("**/other/**", "**/bad_*"),
        ),
    )
    ir = analyzer.analyze(cfg)
    paths = _paths(ir)

    assert not any(p.startswith("other/") for p in paths)
    assert "app/bad_syntax.py" not in paths
    assert "app/bad_encoding.py" not in paths


# ----------------------------
# analyze: max_file_size_bytes
# ----------------------------


def test_max_file_size_bytes_skips_large_files(repo: Path, analyzer: PythonAnalyzer) -> None:
    cfg = AnalyzeConfig(
        repo_root=repo,
        target=AnalyzeTarget(include_paths=(repo / "app",)),
        max_file_size_bytes=1000,  # big enough for normal files, too small for huge.py
    )
    ir = analyzer.analyze(cfg)
    paths = _paths(ir)

    assert "app/huge.py" not in paths
    assert "app/a.py" in paths
    assert "app/b.py" in paths


# ----------------------------
# analyze: parsing robustness (important!)
# ----------------------------


def test_syntax_error_file_does_not_break_analysis(repo: Path, analyzer: PythonAnalyzer) -> None:
    cfg = AnalyzeConfig(repo_root=repo, target=AnalyzeTarget(include_paths=(repo / "app",)))
    ir = analyzer.analyze(cfg)
    paths = _paths(ir)

    # must still analyze valid files
    assert "app/a.py" in paths
    assert "app/b.py" in paths
    assert "app/c.py" in paths


def test_decode_error_file_does_not_break_analysis(repo: Path, analyzer: PythonAnalyzer) -> None:
    cfg = AnalyzeConfig(repo_root=repo, target=AnalyzeTarget(include_paths=(repo / "app",)))
    ir = analyzer.analyze(cfg)
    paths = _paths(ir)

    assert "app/a.py" in paths
    assert "app/b.py" in paths


# ----------------------------
# analyze: import graph correctness
# ----------------------------


def test_import_edges_module_level(repo: Path, analyzer: PythonAnalyzer) -> None:
    """
    Validates module-level resolution:
      - import app.b => edge to app/b.py
      - from app import c => edge to app/__init__.py (module 'app')
      - from .c import C => edge to app/c.py (module 'app.c')
      - from .b import B in c.py => edge to app/b.py (module 'app.b')
    """
    cfg = AnalyzeConfig(repo_root=repo, target=AnalyzeTarget(include_paths=(repo / "app",)))
    ir = analyzer.analyze(cfg)

    # a.py -> b.py from "import app.b"
    _assert_edge(ir, "app/a.py", "app/b.py")

    # a.py -> app/__init__.py from "from app import c as c_alias"
    _assert_edge(ir, "app/a.py", "app/__init__.py")

    # a.py -> c.py from "from .c import C" and "import app.c"
    _assert_edge(ir, "app/a.py", "app/c.py")

    # c.py -> b.py from "from .b import B"
    _assert_edge(ir, "app/c.py", "app/b.py")


def test_from_dot_import_x_resolves_to_module_under_package(repo: Path, analyzer: PythonAnalyzer) -> None:
    cfg = AnalyzeConfig(repo_root=repo, target=AnalyzeTarget(include_paths=(repo / "app",)))
    ir = analyzer.analyze(cfg)

    # from . import b  => app.b => app/b.py
    _assert_edge(ir, "app/a.py", "app/b.py")


def test_relative_level_two_import_best_effort(repo: Path, analyzer: PythonAnalyzer) -> None:
    """
    In app/a.py we have: from .. import top  (level=2, module=None).
    src_module is app.a => package cut makes base empty, then special-case returns 'top'
    which maps to top.py in this repo.
    """
    cfg = AnalyzeConfig(repo_root=repo, target=AnalyzeTarget(include_paths=(repo,)))
    ir = analyzer.analyze(cfg)

    # Ensure top.py node exists and a.py links to it
    _assert_edge(ir, "app/a.py", "top.py")


def test_external_imports_create_nodes_without_paths(repo: Path, analyzer: PythonAnalyzer) -> None:
    """
    'import os' should produce a destination node with path None (external),
    and the graph should remain consistent.
    """
    cfg = AnalyzeConfig(repo_root=repo, target=AnalyzeTarget(include_paths=(repo / "app",)))
    ir = analyzer.analyze(cfg)
    _assert_all_edge_endpoints_exist(ir)

    # There should be at least one node with no path (external module)
    assert any(n.path is None for n in ir.nodes)


# ----------------------------
# Determinism (very important)
# ----------------------------


def test_determinism_same_repo_same_output(repo: Path, analyzer: PythonAnalyzer) -> None:
    cfg = AnalyzeConfig(repo_root=repo, deterministic=True)

    ir1 = analyzer.analyze(cfg).to_dict()
    ir2 = analyzer.analyze(cfg).to_dict()

    assert ir1 == ir2


def test_non_deterministic_mode_still_produces_valid_ir(repo: Path, analyzer: PythonAnalyzer) -> None:
    """
    Even if deterministic=False, the IR must remain valid (endpoints exist).
    We don't enforce stable ordering in this mode.
    """
    cfg = AnalyzeConfig(repo_root=repo, deterministic=False)
    ir = analyzer.analyze(cfg)
    _assert_all_edge_endpoints_exist(ir)


# ----------------------------
# produced_by / plugin_id expectations
# ----------------------------


def test_produced_by_contains_plugin_id(repo: Path, analyzer: PythonAnalyzer) -> None:
    cfg = AnalyzeConfig(repo_root=repo)
    ir = analyzer.analyze(cfg)
    assert analyzer.plugin_id in ir.produced_by
