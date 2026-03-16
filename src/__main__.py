"""CLI entry point: python -m src"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from src.config import MACHINES, REPORTS_DIR, SESSIONS_DIR, WORKFLOWS
from src.logger.session_logger import list_sessions, save_session
from src.models import Session, new_session_id, now_iso
from src.report.generator import generate_report, save_report


def _prompt(label: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def _prompt_choice(label: str, choices: tuple[str, ...]) -> str:
    """Prompt user to pick from a list."""
    print(f"{label}:")
    for i, c in enumerate(choices, 1):
        print(f"  {i}. {c}")
    while True:
        raw = input("Choice: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1]
        if raw in choices:
            return raw
        print(f"  Invalid. Pick 1-{len(choices)} or type the name.")


def _prompt_int(label: str, default: int = 0) -> int:
    """Prompt user for an integer."""
    raw = _prompt(label, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


def _parse_iso(ts: str) -> datetime:
    """Parse ISO 8601 string, assuming UTC if no timezone given."""
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def cmd_record(_args: argparse.Namespace) -> None:
    """Record a benchmark session interactively."""
    print("=== Record Benchmark Session ===\n")

    workflow = _prompt_choice("Workflow", WORKFLOWS)
    task_id = _prompt("Task ID", "scaffold_v1")
    machine = _prompt_choice("Machine", MACHINES)

    started_at = _prompt("Start time (ISO 8601, or 'now')", "now")
    if started_at == "now":
        started_at = now_iso()

    input("\nPress Enter when the session is complete...")

    ended_at = now_iso()
    start_dt = _parse_iso(started_at)
    end_dt = _parse_iso(ended_at)
    duration = (end_dt - start_dt).total_seconds()

    outcome = _prompt_choice("Outcome", ("success", "partial", "failure"))
    error_count = _prompt_int("Error count", 0)
    human_interventions = _prompt_int("Human interventions", 0)
    files_created = _prompt_int("Files created", 0)
    tests_passed = _prompt_int("Tests passed", 0)
    tests_failed = _prompt_int("Tests failed", 0)
    notes = _prompt("Notes (free text)", "")

    session = Session(
        session_id=new_session_id(),
        workflow=workflow,
        task_id=task_id,
        machine=machine,
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=round(duration, 1),
        outcome=outcome,
        error_count=error_count,
        human_interventions=human_interventions,
        files_created=files_created,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        notes=notes,
    )

    path = save_session(session)
    print(f"\nSession saved: {path}")


def cmd_list(args: argparse.Namespace) -> None:
    """List recorded sessions."""
    sessions = list_sessions(
        workflow=args.workflow,
        task_id=args.task,
    )
    if not sessions:
        print("No sessions found.")
        return

    print(f"{'ID':<14} {'Workflow':<6} {'Task':<15} {'Outcome':<9} {'Duration':>10} {'Errors':>7}")
    print("-" * 65)
    for s in sessions:
        mins = s.duration_seconds / 60
        print(
            f"{s.session_id:<14} {s.workflow:<6} {s.task_id:<15} "
            f"{s.outcome:<9} {mins:>8.1f}m {s.error_count:>7}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="grounded-agent",
        description="Benchmark framework for autonomous AI workflow comparison",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("record", help="Record a benchmark session")

    report_parser = sub.add_parser("report", help="Generate Markdown benchmark report")
    report_parser.add_argument(
        "--save", action="store_true", help="Save report to data/reports/",
    )

    list_parser = sub.add_parser("list", help="List recorded sessions")
    list_parser.add_argument("--workflow", choices=WORKFLOWS, default=None)
    list_parser.add_argument("--task", default=None)

    args = parser.parse_args()

    try:
        if args.command == "record":
            cmd_record(args)
        elif args.command == "list":
            cmd_list(args)
        elif args.command == "report":
            if args.save:
                path = save_report(str(SESSIONS_DIR), str(REPORTS_DIR))
                print(f"Report saved: {path}")
            else:
                print(generate_report(str(SESSIONS_DIR)))
        else:
            parser.print_help()
            sys.exit(1)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
