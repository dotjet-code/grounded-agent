#!/usr/bin/env python3
"""Dead-man / runaway checker for the persona autopost agent.

Run by launchd every 15 minutes (com.grounded-agent.persona-heartbeat).
Needs no secrets and imports no project code — it only reads state files
and launchctl, so a bug in the agent cannot take the checker down with it.

Alert conditions:
  A. heartbeat.json older than STALE_HEARTBEAT_HOURS while the job is
     loaded and no STOP file exists  -> the agent went silent
  B. run.lock older than STALE_LOCK_MINUTES -> a run is hung or crashed
  C. STOP file exists but the launchd job is still loaded -> half-stopped

Alerts go to data/logs/safety-alerts.log and, when possible, a macOS
notification. Repeated identical alerts are suppressed for 4 hours.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATE = REPO / "data" / "state"
LOG = REPO / "data" / "logs" / "safety-alerts.log"
SUPPRESS = STATE / "alerts-sent.json"

LABEL = "com.grounded-agent.persona-autopost"
STALE_HEARTBEAT_HOURS = 5  # runs every 4h; +1h grace
STALE_LOCK_MINUTES = 30
SUPPRESS_HOURS = 4


def now() -> datetime:
    return datetime.now(timezone.utc)


def job_loaded() -> bool:
    # Query the gui domain directly: `launchctl list LABEL` fails from
    # non-gui contexts even when the job is loaded (2026-08-08 drill).
    import os

    r = subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{LABEL}"],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def age_hours(path: Path) -> float | None:
    if not path.exists():
        return None
    return (now().timestamp() - path.stat().st_mtime) / 3600


def notify(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{now().isoformat()} ALERT {message}\n")
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                'display notification "'
                + message.replace('"', "'")
                + '" with title "persona-autopost 安全アラート" sound name "Basso"',
            ],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass  # log entry is the source of truth; notification is best-effort


def suppressed(key: str) -> bool:
    try:
        sent = json.loads(SUPPRESS.read_text(encoding="utf-8"))
        last = datetime.fromisoformat(sent[key])
        return (now() - last).total_seconds() < SUPPRESS_HOURS * 3600
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return False


def mark_sent(key: str) -> None:
    try:
        sent = json.loads(SUPPRESS.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        sent = {}
    sent[key] = now().isoformat()
    STATE.mkdir(parents=True, exist_ok=True)
    SUPPRESS.write_text(json.dumps(sent), encoding="utf-8")


def check() -> int:
    alerts: list[tuple[str, str]] = []
    stop_exists = (REPO / "data" / "STOP").exists()
    loaded = job_loaded()

    hb_age = age_hours(STATE / "heartbeat.json")
    if loaded and not stop_exists:
        if hb_age is None:
            alerts.append(("no-heartbeat", "ハートビート未記録(初回設定または沈黙)"))
        elif hb_age > STALE_HEARTBEAT_HOURS:
            alerts.append(
                ("stale-heartbeat", f"エージェント沈黙: 最終実行から{hb_age:.1f}時間")
            )

    lock_age = age_hours(STATE / "run.lock")
    if lock_age is not None and lock_age * 60 > STALE_LOCK_MINUTES:
        alerts.append(
            ("stale-lock", f"実行が{lock_age * 60:.0f}分ハング中(暴走の可能性)")
        )

    if stop_exists and loaded:
        alerts.append(
            ("half-stopped", "STOPファイルありなのにlaunchdジョブが残存(半停止状態)")
        )

    fired = 0
    for key, message in alerts:
        if not suppressed(key):
            notify(message)
            mark_sent(key)
            fired += 1
    return fired


if __name__ == "__main__":
    sys.exit(0 if check() >= 0 else 1)
