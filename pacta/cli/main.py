import argparse
import sys

from pacta.cli import diff, history, scan, snapshot
from pacta.cli.exitcodes import EXIT_ENGINE_ERROR


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pacta", description="Pacta — Architecture testing & architecture-as-code")
    p.add_argument("--version", dest="tool_version", default=None, help="Override tool version for reporting.")

    sub = p.add_subparsers(dest="cmd", required=True)

    # scan
    scan_p = sub.add_parser("scan", help="Scan repository and evaluate rules.")
    scan_p.add_argument("path", nargs="?", default=".", help="Repository root (default: .)")
    scan_p.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")
    scan_p.add_argument("--rules", action="append", default=None, help="Rules file path (repeatable).")
    scan_p.add_argument("--model", default=None, help="Architecture model file (architecture.yaml).")
    scan_p.add_argument("--baseline", default=None, help="Baseline snapshot ref (e.g. baseline).")
    scan_p.add_argument("--mode", choices=["full", "changed_only"], default="full", help="Evaluation mode.")
    scan_p.add_argument(
        "--save-ref", dest="save_ref", default=None, help="Save snapshot under this ref (e.g. baseline)."
    )
    verbosity = scan_p.add_mutually_exclusive_group()
    verbosity.add_argument("-q", "--quiet", action="store_true", help="Minimal output (summary only).")
    verbosity.add_argument("-v", "--verbose", action="store_true", help="Verbose output (include all details).")

    # snapshot
    snap = sub.add_parser("snapshot", help="Snapshot operations.")
    snap_sub = snap.add_subparsers(dest="snapshot_cmd", required=True)

    snap_save = snap_sub.add_parser("save", help="Save architecture snapshot.")
    snap_save.add_argument("path", nargs="?", default=".", help="Repository root (default: .)")
    snap_save.add_argument("--ref", default="latest", help="Snapshot ref (default: latest).")
    snap_save.add_argument("--model", default=None, help="Architecture model file (architecture.yaml).")

    # diff
    diff_p = sub.add_parser("diff", help="Diff two snapshots.")
    diff_p.add_argument("path", nargs="?", default=".", help="Repository root (default: .)")
    diff_p.add_argument("--from", dest="from_ref", required=True, help="From snapshot ref.")
    diff_p.add_argument("--to", dest="to_ref", required=True, help="To snapshot ref.")

    # history
    hist = sub.add_parser("history", help="View architecture history.")
    hist_sub = hist.add_subparsers(dest="history_cmd", required=True)

    hist_show = hist_sub.add_parser("show", help="Show architecture timeline.")
    hist_show.add_argument("path", nargs="?", default=".", help="Repository root (default: .)")
    hist_show.add_argument("--last", type=int, default=None, help="Show only last N entries.")
    hist_show.add_argument("--since", default=None, help="Show entries since date (ISO-8601).")
    hist_show.add_argument("--branch", default=None, help="Filter by branch name.")
    hist_show.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")

    hist_export = hist_sub.add_parser("export", help="Export history for external processing.")
    hist_export.add_argument("path", nargs="?", default=".", help="Repository root (default: .)")
    hist_export.add_argument("--format", choices=["json", "jsonl"], default="json", help="Export format.")
    hist_export.add_argument("--output", "-o", default=None, help="Output file (default: stdout).")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.cmd == "scan":
            rules = tuple(args.rules) if args.rules is not None else None
            verbosity = "quiet" if args.quiet else ("verbose" if args.verbose else "normal")
            return scan.run(
                path=args.path,
                fmt=args.format,
                rules=rules,
                model=args.model,
                baseline=args.baseline,
                mode=args.mode,
                save_ref=args.save_ref,
                verbosity=verbosity,
                tool_version=args.tool_version,
            )

        if args.cmd == "snapshot":
            if args.snapshot_cmd == "save":
                return snapshot.save(
                    path=args.path,
                    ref=args.ref,
                    model=args.model,
                    tool_version=args.tool_version,
                )

        if args.cmd == "diff":
            return diff.snapshot_diff(path=args.path, from_ref=args.from_ref, to_ref=args.to_ref)

        if args.cmd == "history":
            if args.history_cmd == "show":
                return history.show(
                    path=args.path,
                    last=args.last,
                    since=args.since,
                    branch=args.branch,
                    format=args.format,
                )
            if args.history_cmd == "export":
                return history.export(
                    path=args.path,
                    format=args.format,
                    output=args.output,
                )

        print("Unknown command.", file=sys.stderr)
        return EXIT_ENGINE_ERROR

    except Exception as e:
        print(f"pacta: error: {e}", file=sys.stderr)
        return EXIT_ENGINE_ERROR
