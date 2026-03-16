"""Generate Markdown benchmark reports from session JSON files."""

from __future__ import annotations

from pathlib import Path

from src.models import Session


def generate_report(sessions_dir: str) -> str:
    """Read all session JSON files and return a Markdown summary report."""
    directory = Path(sessions_dir)
    sessions: list[Session] = []

    if directory.exists():
        for path in sorted(directory.glob("*.json")):
            text = path.read_text(encoding="utf-8")
            sessions.append(Session.from_json(text))

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
