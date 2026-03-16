"""Generate Markdown benchmark reports from session JSON files."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.models import Session


def _load_sessions(sessions_dir: str) -> list[Session]:
    """Read all session JSON files from a directory."""
    directory = Path(sessions_dir)
    sessions: list[Session] = []
    if directory.exists():
        for path in sorted(directory.glob("*.json")):
            text = path.read_text(encoding="utf-8")
            sessions.append(Session.from_json(text))
    return sessions


def generate_report(sessions_dir: str) -> str:
    """Read all session JSON files and return a Markdown summary report."""
    sessions = _load_sessions(sessions_dir)

    lines: list[str] = ["# Benchmark Report", ""]

    # Table header
    headers = [
        "workflow",
        "task_id",
        "duration_seconds",
        "outcome",
        "error_count",
        "human_interventions",
        "tests_passed",
        "tests_failed",
    ]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")

    # Table rows
    for s in sessions:
        row = [
            s.workflow,
            s.task_id,
            str(s.duration_seconds),
            s.outcome,
            str(s.error_count),
            str(s.human_interventions),
            str(s.tests_passed),
            str(s.tests_failed),
        ]
        lines.append("| " + " | ".join(row) + " |")

    # Totals
    total = len(sessions)
    avg_duration = sum(s.duration_seconds for s in sessions) / total if total else 0.0
    total_errors = sum(s.error_count for s in sessions)
    total_interventions = sum(s.human_interventions for s in sessions)

    lines.append("")
    lines.append("## Totals")
    lines.append("")
    lines.append(f"- Total sessions: {total}")
    lines.append(f"- Average duration: {avg_duration}")
    lines.append(f"- Total errors: {total_errors}")
    lines.append(f"- Total human interventions: {total_interventions}")
    lines.append("")

    return "\n".join(lines)


def save_report(sessions_dir: str, reports_dir: str) -> Path:
    """Generate a report and save it as a timestamped Markdown file.

    The saved file includes a YAML-style metadata header with session IDs,
    task IDs, and workflows for traceability.

    Returns the path of the saved file.
    """
    sessions = _load_sessions(sessions_dir)
    report_body = generate_report(sessions_dir)

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.md"

    # Build metadata header
    meta_lines: list[str] = [
        "---",
        f"generated_at: \"{now.isoformat()}\"",
        f"sessions_count: {len(sessions)}",
    ]

    if sessions:
        session_ids = [s.session_id for s in sessions]
        meta_lines.append(f"session_ids: {session_ids}")

        task_ids = sorted(set(s.task_id for s in sessions))
        meta_lines.append(f"task_ids: {task_ids}")

        workflows = sorted(set(s.workflow for s in sessions))
        meta_lines.append(f"workflows: {workflows}")

    meta_lines.append("---")
    meta_lines.append("")

    full_content = "\n".join(meta_lines) + report_body

    out_dir = Path(reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_text(full_content, encoding="utf-8")

    return out_path
