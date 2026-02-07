from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pacta import PACTA_VERSION
from pacta.core.config import EngineConfig
from pacta.core.engine import DefaultPactaEngine
from pacta.reporting.builder import DefaultReportBuilder
from pacta.reporting.types import Report, RunInfo


def _maybe_call(obj: Any, name: str, *args: Any, **kwargs: Any) -> Any:
    fn = getattr(obj, name, None)
    if callable(fn):
        return fn(*args, **kwargs)
    return None


def run_engine_scan(
    *,
    repo_root: str,
    model_file: str | None,
    rules_files: tuple[str, ...],
    baseline_ref: str | None,
    mode: str,
    save_ref: str | None,
    tool_version: str | None,
) -> Report:
    """
    Try to execute the analysis using pacta.core.engine.DefaultPactaEngine (or compatible).

    Supported patterns (attempted in order):
      1) engine.scan(repo_root=..., model_file=..., rules_files=..., baseline_ref=..., mode=...)
      2) engine.run(...) same args
      3) engine.analyze(...) same args
      4) engine.check(...) same args

    The result may be:
      - Report
      - dict compatible with Report.to_dict()
      - a tuple like (violations, engine_errors, diff)
      - an object with .violations/.engine_errors/.diff

    We normalize to Report using DefaultReportBuilder.
    """

    engine = DefaultPactaEngine()  # default wiring in your core/engine.py

    # Build EngineConfig for the new scan() signature
    cfg = EngineConfig(
        repo_root=Path(repo_root),
        model_file=Path(model_file) if model_file else None,
        rules_files=tuple(Path(f) for f in rules_files),
        baseline=baseline_ref,
        changed_only=(mode == "changed_only"),
        save_ref=save_ref,
    )

    # Try new scan(cfg) signature first
    result = _maybe_call(engine, "scan", cfg)
    if result is not None:
        # scan() returns ScanResult, extract the report
        if hasattr(result, "report"):
            return result.report
        # Fall through to handle as before
        res = result
    else:
        # Fallback: try old-style methods with kwargs
        payload = dict(
            repo_root=repo_root,
            model_file=model_file,
            rules_files=rules_files,
            baseline_ref=baseline_ref,
            mode=mode,
        )
        res = (
            _maybe_call(engine, "run", **payload)
            or _maybe_call(engine, "analyze", **payload)
            or _maybe_call(engine, "check", **payload)
        )

    # If engine already returns a Report, pass through.
    if isinstance(res, Report):
        return res

    run = RunInfo(
        repo_root=repo_root,
        commit=None,
        branch=None,
        model_file=model_file,
        rules_files=rules_files,
        baseline_ref=baseline_ref,
        mode="changed_only" if mode == "changed_only" else "full",
        created_at=None,
        tool_version=tool_version,
        metadata={},
    )

    builder = DefaultReportBuilder(tool="pacta", version=tool_version or PACTA_VERSION)

    if isinstance(res, Mapping):
        violations = res.get("violations", ())
        engine_errors = res.get("engine_errors", ())
        diff = res.get("diff", None)
        if "tool" in res and "run" in res and "summary" in res:
            return builder.build(run=run, violations=violations, engine_errors=engine_errors, diff=diff)
        return builder.build(run=run, violations=violations, engine_errors=engine_errors, diff=diff)

    # tuple pattern
    if isinstance(res, tuple) and len(res) in (2, 3):
        violations = res[0]
        engine_errors = res[1]
        diff = res[2] if len(res) == 3 else None
        return builder.build(run=run, violations=violations, engine_errors=engine_errors, diff=diff)

    # object with attributes
    if res is not None and (hasattr(res, "violations") or hasattr(res, "engine_errors")):
        violations = getattr(res, "violations", ())
        engine_errors = getattr(res, "engine_errors", ())
        diff = getattr(res, "diff", None)
        return builder.build(run=run, violations=violations, engine_errors=engine_errors, diff=diff)

    # Nothing usable returned
    return builder.build(run=run, violations=(), engine_errors=())
