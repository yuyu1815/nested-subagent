"""Generate dummy JSONL data and launch TUI for visual testing."""
from __future__ import annotations

import asyncio
import time
from src.storage import append_event, clear_tasks, TASKS_DIR


def create_dummy_tasks() -> None:
    clear_tasks()

    # Task 1: Completed task
    tid1 = "a1b2c3d4"
    append_event(tid1, {"type": "init", "prompt": "Fix authentication bug in login flow", "model": "sonnet"})
    append_event(tid1, {"type": "tool_start", "name": "Read", "tool_id": "t1", "args": "src/auth/login.py"})
    append_event(tid1, {"type": "tool_end", "tool_id": "t1", "status": "ok", "duration_ms": 312, "detail": "Read 142 lines"})
    append_event(tid1, {"type": "tool_start", "name": "Grep", "tool_id": "t2", "args": "session_token"})
    append_event(tid1, {"type": "tool_end", "tool_id": "t2", "status": "ok", "duration_ms": 89, "detail": "Found 3 matches in 2 files"})
    append_event(tid1, {"type": "tool_start", "name": "Edit", "tool_id": "t3", "args": "src/auth/login.py"})
    append_event(tid1, {"type": "tool_end", "tool_id": "t3", "status": "ok", "duration_ms": 2100, "detail": "lines 42-58: added token validation"})
    append_event(tid1, {"type": "tool_start", "name": "Bash", "tool_id": "t4", "args": "pytest tests/auth/"})
    append_event(tid1, {"type": "tool_end", "tool_id": "t4", "status": "ok", "duration_ms": 4200, "detail": "12 passed, 0 failed"})
    append_event(tid1, {"type": "result", "content": "Fixed the authentication bug by adding proper session token validation in the login flow. All tests pass.", "duration_ms": 8500})

    # Task 2: Running task (no result yet)
    tid2 = "e5f6g7h8"
    append_event(tid2, {"type": "init", "prompt": "Refactor database connection pooling", "model": "opus"})
    append_event(tid2, {"type": "tool_start", "name": "Glob", "tool_id": "t5", "args": "src/**/*.py"})
    append_event(tid2, {"type": "tool_end", "tool_id": "t5", "status": "ok", "duration_ms": 150, "detail": "Found 28 files"})
    append_event(tid2, {"type": "tool_start", "name": "Read", "tool_id": "t6", "args": "src/db/pool.py"})
    append_event(tid2, {"type": "tool_end", "tool_id": "t6", "status": "ok", "duration_ms": 200, "detail": "Read 89 lines"})
    append_event(tid2, {"type": "tool_start", "name": "Edit", "tool_id": "t7", "args": "src/db/pool.py"})
    # No tool_end yet - still running

    # Task 3: Failed task
    tid3 = "i9j0k1l2"
    append_event(tid3, {"type": "init", "prompt": "Deploy to staging environment", "model": "haiku"})
    append_event(tid3, {"type": "tool_start", "name": "Bash", "tool_id": "t8", "args": "kubectl apply -f deploy.yaml"})
    append_event(tid3, {"type": "tool_end", "tool_id": "t8", "status": "error", "duration_ms": 3400, "detail": "Error: connection refused to cluster"})

    print(f"Created 3 dummy tasks in {TASKS_DIR}")
    print(f"  - {tid1}: completed (4 tools, 8.5s)")
    print(f"  - {tid2}: running (3 tools, edit in progress)")
    print(f"  - {tid3}: error (deploy failed)")


if __name__ == "__main__":
    create_dummy_tasks()

    # Launch TUI
    from src.tui.app import AgentViewerApp
    app = AgentViewerApp()
    app.run()
