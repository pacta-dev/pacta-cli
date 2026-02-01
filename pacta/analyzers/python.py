import ast
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pacta.ir.keys import edge_key, node_key
from pacta.ir.types import (
    ArchitectureIR,
    CanonicalId,
    DepType,
    IREdge,
    IRNode,
    Language,
    SourceLoc,
    SourcePos,
    SymbolKind,
)
from pacta.plugins.interfaces.analyzer import AnalyzeConfig, AnalyzeTarget


@dataclass(frozen=True, slots=True)
class _ImportHit:
    """
    Internal representation of a single import statement occurrence.
    """

    kind: str  # "import" | "from"
    module: str | None  # for "from X import Y" => X (may be None)
    name: str | None  # for "import X" => X; for "from X import Y" => Y
    level: int  # relative import level (0 = absolute)
    lineno: int
    col_offset: int


class PythonAnalyzer:
    """
    Python analyzer plugin.

    MVP scope:
    - module-level nodes from *.py files
    - module-level import edges
    - best-effort external nodes (no path/loc)
    """

    @property
    def language(self) -> Language:
        return Language.PYTHON

    @property
    def plugin_id(self) -> str:
        return "pacta-python"

    _DEFAULT_EXCLUDE_GLOBS: tuple[str, ...] = (
        "**/.git/**",
        "**/.hg/**",
        "**/.svn/**",
        "**/__pycache__/**",
        "**/.mypy_cache/**",
        "**/.pytest_cache/**",
        "**/.ruff_cache/**",
        "**/.venv/**",
        "**/venv/**",
        "**/env/**",
        "**/dist/**",
        "**/build/**",
        "**/*.egg-info/**",
        "**/site-packages/**",
    )

    def can_analyze(self, repo_root: Path) -> bool:
        """
        Fast check: find at least one *.py file, ignoring default excluded dirs.
        Must NOT do deep parsing.
        """
        repo_root = repo_root.resolve()
        if not repo_root.exists():
            return False

        # very lightweight scan
        for p in repo_root.rglob("*.py"):
            if p.is_file() and not self._is_excluded(repo_root, p, self._DEFAULT_EXCLUDE_GLOBS):
                return True
        return False

    def analyze(self, config: AnalyzeConfig) -> ArchitectureIR:
        repo_root = config.normalized_repo_root()

        target = config.target if config.target is not None else AnalyzeTarget()
        include_paths = self._normalize_includes(repo_root, target)
        exclude_globs = self._merge_excludes(target)

        py_files = list(self._iter_python_files(repo_root, include_paths, exclude_globs, config.max_file_size_bytes))
        if config.deterministic:
            py_files.sort(key=lambda p: p.as_posix())

        # Stable code_root for CanonicalId: repo folder name (avoid machine-specific abs paths)
        code_root = repo_root.name

        nodes: list[IRNode] = []
        edges: list[IREdge] = []

        file_to_mod: dict[Path, str] = {}

        # 1) create module nodes (from files)
        for f in py_files:
            mod = self._module_fqname_from_path(repo_root, f)
            file_to_mod[f] = mod
            rel = f.relative_to(repo_root).as_posix()
            nodes.append(
                IRNode(
                    id=CanonicalId(language=Language.PYTHON, code_root=code_root, fqname=mod),
                    kind=SymbolKind.MODULE,
                    name=mod.rsplit(".", 1)[-1] if mod else f.stem,
                    path=rel,
                    loc=SourceLoc(
                        file=rel,
                        start=SourcePos(line=1, column=1),
                        end=None,
                    ),
                )
            )

        # 2) parse imports and create edges (+ best-effort external module nodes)
        for f in py_files:
            rel = f.relative_to(repo_root).as_posix()
            src_mod = file_to_mod.get(f) or self._module_fqname_from_path(repo_root, f)
            src_id = CanonicalId(language=Language.PYTHON, code_root=code_root, fqname=src_mod)

            try:
                text = f.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # skip unreadable file
                continue

            try:
                tree = ast.parse(text, filename=rel)
            except SyntaxError:
                # skip invalid python file
                continue

            for imp in self._iter_imports(tree):
                dst_mod = self._resolve_import_target_module(src_mod, imp)
                if not dst_mod:
                    continue

                dst_id = CanonicalId(language=Language.PYTHON, code_root=code_root, fqname=dst_mod)

                # Ensure dependency node exists (may be external => path None)
                nodes.append(
                    IRNode(
                        id=dst_id,
                        kind=SymbolKind.MODULE,
                        name=dst_mod.rsplit(".", 1)[-1],
                        path=None,
                        loc=None,
                    )
                )

                edges.append(
                    IREdge(
                        src=src_id,
                        dst=dst_id,
                        dep_type=DepType.IMPORT,
                        loc=self._edge_loc(rel, imp.lineno, imp.col_offset),
                        confidence=1.0,
                        details={
                            "kind": imp.kind,
                            "module": imp.module,
                            "name": imp.name,
                            "level": imp.level,
                        },
                    )
                )

        # 3) deterministically dedupe + order
        nodes_t = tuple(self._dedupe_nodes(nodes, deterministic=config.deterministic))
        edges_t = tuple(self._dedupe_edges(edges, deterministic=config.deterministic))

        return ArchitectureIR(
            schema_version=1,
            produced_by=f"{self.plugin_id}@0.1.0",
            repo_root=str(repo_root),
            nodes=nodes_t,
            edges=edges_t,
            metadata={
                "language": self.language.value,
                "files_scanned": len(py_files),
                "include_paths": [p.relative_to(repo_root).as_posix() for p in include_paths],
                "exclude_globs": list(exclude_globs),
            },
        )

    def _normalize_includes(self, repo_root: Path, target: AnalyzeTarget) -> tuple[Path, ...]:
        """
        If target.include_paths is empty -> analyze entire repo_root.
        Otherwise resolve each include path relative to repo_root.
        """
        if not target.include_paths:
            return (repo_root,)

        inc: list[Path] = []
        for p in target.include_paths:
            pp = p
            if not pp.is_absolute():
                pp = repo_root / pp
            pp = pp.resolve()
            # safety: avoid scanning outside repo
            try:
                pp.relative_to(repo_root)
            except Exception:
                continue
            inc.append(pp)
        return tuple(inc) if inc else (repo_root,)

    def _merge_excludes(self, target: AnalyzeTarget) -> tuple[str, ...]:
        globs = list(self._DEFAULT_EXCLUDE_GLOBS)
        globs.extend(list(target.exclude_globs or ()))
        return tuple(globs)

    def _iter_python_files(
        self,
        repo_root: Path,
        include_paths: tuple[Path, ...],
        exclude_globs: tuple[str, ...],
        max_file_size_bytes: int,
    ) -> Iterator[Path]:
        for base in include_paths:
            if base.is_file():
                if base.suffix == ".py" and not self._is_excluded(repo_root, base, exclude_globs):
                    if base.stat().st_size <= max_file_size_bytes:
                        yield base
                continue

            if not base.exists():
                continue

            for f in base.rglob("*.py"):
                if not f.is_file():
                    continue
                if self._is_excluded(repo_root, f, exclude_globs):
                    continue
                try:
                    if f.stat().st_size > max_file_size_bytes:
                        continue
                except OSError:
                    continue
                yield f

    def _is_excluded(self, repo_root: Path, path: Path, exclude_globs: tuple[str, ...]) -> bool:
        """
        Match repo-relative POSIX path against glob patterns supporting ** semantics.

        We avoid Path.match quirks and fnmatch limitations by translating globs to regex.
        """
        try:
            rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
        except Exception:
            return True

        for g in exclude_globs:
            gg = g.replace("\\", "/")
            if self._glob_match(rel, gg):
                return True

        return False

    @staticmethod
    @lru_cache(maxsize=2048)
    def _glob_to_regex(pattern: str) -> re.Pattern[str]:
        """
        Translate a glob pattern to a compiled regex, supporting:
          - **  => match zero or more path segments
          - *   => [^/]*
          - ?   => [^/]
        The match is anchored (full string match).
        """
        # Build regex manually to handle ** specially
        i = 0
        n = len(pattern)
        out: list[str] = ["^"]
        while i < n:
            c = pattern[i]
            if c == "*":
                # check for **
                if i + 1 < n and pattern[i + 1] == "*":
                    # ** should match zero or more path segments
                    # Look ahead to see if there's a / after **
                    if i + 2 < n and pattern[i + 2] == "/":
                        # **/ at the start or after / should match zero or more segments
                        # Use (?:(?:.*/)|) to match either "anything/" or nothing
                        if i == 0 or (i > 0 and pattern[i - 1] == "/"):
                            out.append("(?:(?:.*/)|)")
                        else:
                            out.append("(?:(?:.*/)|)")
                        i += 3  # skip **, and /
                    else:
                        # ** not followed by / - match rest of path
                        out.append(".*")
                        i += 2
                else:
                    out.append("[^/]*")
                    i += 1
            elif c == "?":
                out.append("[^/]")
                i += 1
            else:
                out.append(re.escape(c))
                i += 1
        out.append("$")
        return re.compile("".join(out))

    @classmethod
    def _glob_match(cls, rel_posix_path: str, pattern: str) -> bool:
        return cls._glob_to_regex(pattern).match(rel_posix_path) is not None

    def _module_fqname_from_path(self, repo_root: Path, f: Path) -> str:
        rel = f.resolve().relative_to(repo_root.resolve())
        parts = list(rel.parts)

        # strip ".py"
        if parts and parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]

        # __init__.py => package module
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]

        if not parts:
            return f.stem

        return ".".join(parts)

    def _iter_imports(self, tree: ast.AST) -> Iterator[_ImportHit]:
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for alias in n.names:
                    yield _ImportHit(
                        kind="import",
                        module=None,
                        name=alias.name,
                        level=0,
                        lineno=getattr(n, "lineno", 1),
                        col_offset=getattr(n, "col_offset", 0),
                    )
            elif isinstance(n, ast.ImportFrom):
                # n.module can be None (e.g., from . import x)
                for alias in n.names:
                    yield _ImportHit(
                        kind="from",
                        module=n.module,
                        name=alias.name,
                        level=int(n.level or 0),
                        lineno=getattr(n, "lineno", 1),
                        col_offset=getattr(n, "col_offset", 0),
                    )

    def _resolve_import_target_module(self, src_module: str, imp: _ImportHit) -> str | None:
        """
        Resolve the *module* dependency target (module-level graph).

        - import a.b        => a.b
        - from a.b import c => a.b
        - from .c import C  => <resolved_base> (e.g. app.c)
        - from . import b   => <resolved_base>.<name> (e.g. app.b)
        - from .. import top => top
        """
        if imp.kind == "import":
            return imp.name

        # from-import
        module = imp.module or ""
        base = module

        if imp.level > 0:
            base = self._resolve_relative_base(src_module, imp.level, module)

        if base:
            # if "from X import Y", the dependency is X (module-level)
            return base

        # module is empty (e.g. "from . import b" or "from .. import top")
        # For those, base resolved above is "" for reaching repo root.
        if imp.name and imp.name != "*":
            # if base is empty, import refers to top-level module
            # otherwise it would have returned earlier.
            # So: from .. import top -> "top"
            # and from . import b where base becomes "app" is handled earlier by returning base.
            return imp.name

        return None

    def _resolve_relative_base(self, src_module: str, level: int, module: str) -> str:
        """
        Resolve relative import base.

        Example:
          src_module="a.b.c"
          from ..x import y  (level=2, module="x") => "a.x"
        """
        src_parts = src_module.split(".") if src_module else []
        cut = max(0, len(src_parts) - level)
        base_parts = src_parts[:cut]
        if module:
            base_parts.extend(module.split("."))
        return ".".join([p for p in base_parts if p])

    def _edge_loc(self, file: str, lineno: int, col_offset: int) -> SourceLoc:
        return SourceLoc(
            file=file,
            start=SourcePos(line=max(1, int(lineno)), column=max(1, int(col_offset) + 1)),
            end=None,
        )

    def _dedupe_nodes(self, nodes: Iterable[IRNode], *, deterministic: bool) -> list[IRNode]:
        """
        Dedupe by node_key() with deterministic tie-breaking (keep first).
        Then optionally sort by key for stability.
        """
        seen: dict[str, IRNode] = {}
        for n in nodes:
            k = node_key(n)
            if k not in seen:
                seen[k] = n

        out = list(seen.values())
        if deterministic:
            out.sort(key=lambda n: node_key(n))
        return out

    def _dedupe_edges(self, edges: Iterable[IREdge], *, deterministic: bool) -> list[IREdge]:
        """
        Dedupe by edge_key() (without location/details) with deterministic tie-breaking (keep first).
        Then optionally sort by key for stability.
        """
        seen: dict[str, IREdge] = {}
        for e in edges:
            k = edge_key(e, include_location=False, include_details=False)
            if k not in seen:
                seen[k] = e

        out = list(seen.values())
        if deterministic:
            out.sort(key=lambda e: edge_key(e, include_location=False, include_details=False))
        return out
