from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = PROJECT_ROOT / ".claude" / "tasks"


def ensure_dir() -> None:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)


def task_path(task_id: str) -> Path:
    return TASKS_DIR / f"{task_id}.jsonl"


def append_event(task_id: str, event: dict) -> None:
    """Append a single event line to a task's JSONL file."""
    ensure_dir()
    event["ts"] = datetime.now(timezone.utc).isoformat()
    event["task_id"] = task_id
    with open(task_path(task_id), "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_events(task_id: str) -> list[dict]:
    """Read all events for a task."""
    path = task_path(task_id)
    if not path.exists():
        return []
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def list_task_ids() -> list[str]:
    """Return task IDs sorted by creation time (newest first)."""
    ensure_dir()
    files = sorted(TASKS_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [p.stem for p in files]


def clear_tasks() -> None:
    """Remove all task JSONL files."""
    ensure_dir()
    for p in TASKS_DIR.glob("*.jsonl"):
        p.unlink()
