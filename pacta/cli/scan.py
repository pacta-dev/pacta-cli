from pacta.cli._engine_adapter import run_engine_scan
from pacta.cli._io import default_model_file, default_rules_files, ensure_repo_root
from pacta.cli._trends import attach_trends
from pacta.cli.exitcodes import exit_code_from_report_dict
from pacta.reporting.renderers.github import GitHubReportRenderer
from pacta.reporting.renderers.json import JsonReportRenderer
from pacta.reporting.renderers.text import TextReportRenderer


def run(
    *,
    path: str,
    fmt: str,
    rules: tuple[str, ...] | None,
    model: str | None,
    baseline: str | None,
    mode: str,
    save_ref: str | None,
    verbosity: str = "normal",
    tool_version: str | None,
) -> int:
    repo_root = ensure_repo_root(path)

    rules_files = rules if rules is not None else default_rules_files(repo_root)
    model_file = model if model is not None else default_model_file(repo_root)

    report = run_engine_scan(
        repo_root=repo_root,
        model_file=model_file,
        rules_files=rules_files,
        baseline_ref=baseline,
        mode=mode,
        save_ref=save_ref,
        tool_version=tool_version,
    )

    if fmt == "github":
        report = attach_trends(report, repo_root=repo_root)
        out = GitHubReportRenderer().render(report)
    elif fmt == "json":
        out = JsonReportRenderer().render(report)
    else:
        out = TextReportRenderer(verbosity=verbosity).render(report)  # type: ignore[arg-type]
    print(out, end="")

    return exit_code_from_report_dict(report.to_dict())
