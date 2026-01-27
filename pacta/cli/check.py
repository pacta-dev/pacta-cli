from pathlib import Path

from pacta.cli._io import default_model_file, default_rules_files, ensure_repo_root
from pacta.cli.exitcodes import exit_code_from_report_dict
from pacta.core.config import EngineConfig
from pacta.core.engine import DefaultPactaEngine
from pacta.reporting.renderers.json import JsonReportRenderer
from pacta.reporting.renderers.text import TextReportRenderer
from pacta.snapshot.store import FsSnapshotStore


def run(
    *,
    path: str,
    ref: str,
    fmt: str,
    rules: tuple[str, ...] | None,
    model: str | None,
    baseline: str | None,
    save_ref: str | None,
    verbosity: str = "normal",
    tool_version: str | None,
) -> int:
    """
    Evaluate rules against an existing snapshot.

    Loads the snapshot identified by --ref, evaluates architecture rules,
    and saves the updated snapshot (with violations) back to the store.
    """
    repo_root = ensure_repo_root(path)

    rules_files = rules if rules is not None else default_rules_files(repo_root)
    model_file = model if model is not None else default_model_file(repo_root)

    # Load existing snapshot
    store = FsSnapshotStore(repo_root=repo_root)
    if not store.exists(ref):
        import sys

        print(f"pacta: error: snapshot ref '{ref}' not found. Run `pacta snapshot save` first.", file=sys.stderr)
        from pacta.cli.exitcodes import EXIT_ENGINE_ERROR

        return EXIT_ENGINE_ERROR

    snapshot = store.load(ref)

    # Build config
    cfg = EngineConfig(
        repo_root=Path(repo_root),
        model_file=Path(model_file) if model_file else None,
        rules_files=tuple(Path(f) for f in rules_files),
        baseline=baseline,
        changed_only=False,
        save_ref=save_ref,
    )

    # Run check
    engine = DefaultPactaEngine()
    result = engine.check(cfg, snapshot)

    # Update existing snapshot object in-place with violations
    short_hash = store.resolve_ref(ref)
    if short_hash is None:
        # ref was a direct hash
        short_hash = ref
    store.update_object(short_hash, result.snapshot)

    # Optionally save under an additional ref
    if save_ref and save_ref != ref:
        store.save(result.snapshot, refs=[save_ref])

    # Render report
    if fmt == "json":
        out = JsonReportRenderer().render(result.report)
    else:
        out = TextReportRenderer(verbosity=verbosity).render(result.report)  # type: ignore[arg-type]
    print(out, end="")

    return exit_code_from_report_dict(result.report.to_dict())
