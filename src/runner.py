from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk import (
    ToolUseBlock,
    ToolResultBlock,
    TextBlock,
    AssistantMessage,
    ResultMessage,
)

from src.storage import append_event

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = PROJECT_ROOT / ".claude" / "debug.log"

SUBAGENT_PROMPT_APPEND = (
    "# レスポンスルール\n"
    "\n"
    "あなたは委任されたタスクを実行するサブエージェントです。\n"
    "\n"
    "## 返却に含めるもの\n"
    "- タスクへの直接の回答（これが最優先）\n"
    "- 発見した重要なデータ（ファイルパス、行番号、値）\n"
    "- エラーが起きた場合：何が失敗し、なぜか\n"
    "\n"
    "## 返却に含めないもの\n"
    "- 作業過程の説明（「ファイルを読みました」「調査しました」）\n"
    "- 謝罪や前置き\n"
    "- 頼まれていない提案や改善案\n"
    "\n"
    "## フォーマット\n"
    "- 回答を先頭に置く\n"
    "- 複数項目はリスト・テーブルで構造化する\n"
    "- 特に指定がなければ2000文字以内\n"
)


def _log(msg: str) -> None:
    """Append a debug line to the log file."""
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat()
    with open(LOG_PATH, "a") as f:
        f.write(f"[{ts}] [runner] {msg}\n")


async def run_task(
    task_id: str,
    prompt: str,
    model: str = "sonnet",
    cwd: str | None = None,
    resume: str | None = None,
    system_prompt: str | None = None,
    allowed_tools: list[str] | None = None,
    disallowed_tools: list[str] | None = None,
    max_budget_usd: float | None = None,
    timeout: int = 600000,
) -> AsyncIterator[dict]:
    """Run a Claude Agent SDK task and yield structured events."""
    start = time.monotonic()
    _log(f"run_task start: task_id={task_id} model={model} cwd={cwd}")

    # Build SDK options dict
    options_dict: dict[str, Any] = {"model": model}
    options_dict["permission_mode"] = "bypassPermissions"
    if system_prompt:
        options_dict["system_prompt"] = system_prompt
    else:
        options_dict["system_prompt"] = {
            "type": "preset",
            "preset": "claude_code",
            "append": SUBAGENT_PROMPT_APPEND,
        }
    if cwd:
        options_dict["cwd"] = cwd
    if resume:
        options_dict["resume"] = resume
    if allowed_tools:
        options_dict["allowed_tools"] = allowed_tools
    if disallowed_tools:
        options_dict["disallowed_tools"] = disallowed_tools
    if max_budget_usd:
        options_dict["max_budget_usd"] = max_budget_usd

    _log(f"options built: {list(options_dict.keys())}")
    options = ClaudeAgentOptions(**options_dict)

    # Init event
    init_event = {"type": "init", "prompt": prompt, "model": model}
    append_event(task_id, init_event)
    yield init_event

    tool_starts: dict[str, float] = {}
    last_result_text = ""

    try:
        async with asyncio.timeout(timeout / 1000):
            _log("query() starting")
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    content = getattr(message, "content", None)
                    if content and isinstance(content, list):
                        for block in content:
                            if isinstance(block, ToolUseBlock):
                                tool_id = block.id
                                tool_name = block.name
                                tool_input = block.input
                                tool_starts[tool_id] = time.monotonic()

                                args_summary = ""
                                if isinstance(tool_input, dict):
                                    for v in tool_input.values():
                                        if isinstance(v, str):
                                            args_summary = v[:100]
                                            break

                                ev = {
                                    "type": "tool_start",
                                    "name": tool_name,
                                    "tool_id": tool_id,
                                    "args": args_summary,
                                }
                                append_event(task_id, ev)
                                _log(f"tool_start: {tool_name}")
                                yield ev

                            elif isinstance(block, ToolResultBlock):
                                tool_id = block.tool_use_id
                                dur = 0
                                if tool_id in tool_starts:
                                    dur = int((time.monotonic() - tool_starts.pop(tool_id)) * 1000)

                                content_text = ""
                                block_content = block.content
                                if isinstance(block_content, str):
                                    content_text = block_content[:200]
                                elif isinstance(block_content, list):
                                    for c in block_content:
                                        if isinstance(c, dict) and c.get("type") == "text":
                                            content_text = c.get("text", "")[:200]
                                            break

                                is_error = block.is_error or False
                                ev = {
                                    "type": "tool_end",
                                    "tool_id": tool_id,
                                    "status": "error" if is_error else "ok",
                                    "duration_ms": dur,
                                    "detail": content_text,
                                }
                                append_event(task_id, ev)
                                _log(f"tool_end: {tool_id} status={'error' if is_error else 'ok'}")
                                yield ev

                            elif isinstance(block, TextBlock):
                                text = block.text
                                if text:
                                    last_result_text = text
                                    elapsed = int((time.monotonic() - start) * 1000)
                                    ev = {"type": "result", "content": text, "duration_ms": elapsed}
                                    append_event(task_id, ev)
                                    _log(f"result: {len(text)} chars, {elapsed}ms")
                                    yield ev

                elif isinstance(message, ResultMessage):
                    session_id = getattr(message, "session_id", None)
                    cost_usd = getattr(message, "total_cost_usd", None)
                    _log(f"ResultMessage: session_id={session_id} cost_usd={cost_usd}")
                    elapsed = int((time.monotonic() - start) * 1000)
                    done_ev = {
                        "type": "done",
                        "session_id": session_id,
                        "cost_usd": cost_usd,
                        "duration_ms": elapsed,
                    }
                    append_event(task_id, done_ev)
                    yield done_ev

    except TimeoutError:
        elapsed = int((time.monotonic() - start) * 1000)
        _log(f"TIMEOUT after {elapsed}ms")
        if last_result_text:
            ev = {"type": "result", "content": last_result_text, "duration_ms": elapsed}
            append_event(task_id, ev)
            yield ev
        else:
            error_ev = {
                "type": "error",
                "content": f"Task timed out after {timeout}ms",
                "duration_ms": elapsed,
            }
            append_event(task_id, error_ev)
            yield error_ev

    except Exception as e:
        elapsed = int((time.monotonic() - start) * 1000)
        _log(f"ERROR: {type(e).__name__}: {e}")
        if last_result_text:
            ev = {"type": "result", "content": last_result_text, "duration_ms": elapsed}
            append_event(task_id, ev)
            yield ev
        else:
            error_ev = {
                "type": "error",
                "content": f"{type(e).__name__}: {e}",
                "duration_ms": elapsed,
            }
            append_event(task_id, error_ev)
            yield error_ev
