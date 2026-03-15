"""Save, load, and list benchmark sessions as JSON files."""

from __future__ import annotations

from pathlib import Path

from src.config import SESSIONS_DIR
from src.models import Session


def save_session(session: Session, base_dir: Path = SESSIONS_DIR) -> Path:
    """Save a session to a JSON file. Returns the file path."""
    base_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{session.workflow}_{session.task_id}_{session.session_id}.json"
    path = base_dir / filename
    path.write_text(session.to_json(), encoding="utf-8")
    return path


def load_session(path: Path) -> Session:
    """Load a session from a JSON file."""
    return Session.from_json(path.read_text(encoding="utf-8"))


def list_sessions(
    base_dir: Path = SESSIONS_DIR,
    workflow: str | None = None,
    task_id: str | None = None,
) -> list[Session]:
    """List all saved sessions, optionally filtered by workflow or task."""
    if not base_dir.exists():
        return []
    sessions = []
    for path in sorted(base_dir.glob("*.json")):
        session = load_session(path)
        if workflow and session.workflow != workflow:
            continue
        if task_id and session.task_id != task_id:
            continue
        sessions.append(session)
    return sessions
