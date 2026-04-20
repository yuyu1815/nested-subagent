from __future__ import annotations

import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP

from src.runner import run_task
from src.storage import append_event

LOG_PATH = Path("/tmp/nested-subagent-debug.log")

mcp = FastMCP(
    name="nested-subagent",
    instructions="Nested subagent with TUI viewer. Runs Claude Agent SDK tasks, saves JSONL, shows real-time TUI.",
)

_tui_process: subprocess.Popen | None = None


def _log(msg: str) -> None:
    """Append a debug line to the log file."""
    ts = datetime.now(timezone.utc).isoformat()
    with open(LOG_PATH, "a") as f:
        f.write(f"[{ts}] [server] {msg}\n")


def _ensure_tui() -> None:
    """Launch TUI viewer if not already running."""
    global _tui_process
    if _tui_process is not None and _tui_process.poll() is None:
        return
    try:
        _tui_process = subprocess.Popen(
            [sys.executable, "-m", "src.tui.app"],
            start_new_session=True,
        )
        _log("TUI launched")
    except Exception as e:
        _log(f"TUI launch failed: {e}")


@mcp.tool()
async def task(
    prompt: Annotated[str, "Task prompt for the agent"],
    model: Annotated[str, "Model: sonnet, opus, or haiku"] = "sonnet",
    cwd: Annotated[str | None, "Working directory for the agent"] = None,
    system_prompt: Annotated[str | None, "Custom system prompt"] = None,
    allowed_tools: Annotated[list[str] | None, "List of allowed tools"] = None,
    disallowed_tools: Annotated[list[str] | None, "List of disallowed tools"] = None,
    max_budget_usd: Annotated[float | None, "Cost limit in USD"] = None,
    timeout: Annotated[int | None, "Timeout in milliseconds"] = 600000,
) -> str:
    """Run a nested Claude agent task. Results are streamed to TUI and saved as JSONL."""
    task_id = uuid.uuid4().hex[:8]
    _log(f"task called: task_id={task_id} model={model} prompt={prompt[:80]}")

    _ensure_tui()

    result_text = ""
    tool_count = 0

    try:
        async for event in run_task(
            task_id=task_id,
            prompt=prompt,
            model=model,
            cwd=cwd,
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            disallowed_tools=disallowed_tools,
            max_budget_usd=max_budget_usd,
            timeout=timeout or 600000,
        ):
            if event["type"] == "tool_start":
                tool_count += 1
            elif event["type"] == "result":
                result_text = event.get("content", "")
            elif event["type"] == "error":
                result_text = f"Error: {event.get('content', 'unknown error')}"
    except Exception as e:
        _log(f"task {task_id} FAILED: {type(e).__name__}: {e}")
        result_text = f"Error: {type(e).__name__}: {e}"

    if not result_text:
        result_text = f"Task {task_id} completed. Tools used: {tool_count}"

    _log(f"task {task_id} done: {len(result_text)} chars")
    return result_text


if __name__ == "__main__":
    _log("MCP server starting")
    mcp.run(transport="stdio")
