from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
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


async def run_task(
    task_id: str,
    prompt: str,
    model: str = "sonnet",
    system_prompt: str | None = None,
    allowed_tools: list[str] | None = None,
    disallowed_tools: list[str] | None = None,
    max_budget_usd: float | None = None,
    timeout: int = 600000,  # ms, default 10 minutes
) -> AsyncIterator[dict]:
    """Run a Claude Agent SDK task and yield structured events.

    Each yielded dict is also persisted to JSONL via storage.
    """
    start = time.monotonic()

    # Build SDK options dict
    options_dict: dict[str, Any] = {"model": model}
    options_dict["permission_mode"] = "bypassPermissions"
    if system_prompt:
        options_dict["system_prompt"] = system_prompt
    if allowed_tools:
        options_dict["allowed_tools"] = allowed_tools
    if disallowed_tools:
        options_dict["disallowed_tools"] = disallowed_tools
    if max_budget_usd:
        options_dict["max_budget_usd"] = max_budget_usd

    options = ClaudeAgentOptions(**options_dict)

    # Init event
    init_event = {"type": "init", "prompt": prompt, "model": model}
    append_event(task_id, init_event)
    yield init_event

    tool_starts: dict[str, float] = {}
    last_result_text = ""  # Track for error recovery

    try:
        async with asyncio.timeout(timeout / 1000):
            async for message in query(prompt=prompt, options=options):
                # Process AssistantMessage (contains tool use, text, thinking blocks)
                if isinstance(message, AssistantMessage):
                    content = getattr(message, "content", None)
                    if content and isinstance(content, list):
                        for block in content:
                            if isinstance(block, ToolUseBlock):
                                # Tool invocation started
                                tool_id = block.id
                                tool_name = block.name
                                tool_input = block.input
                                tool_starts[tool_id] = time.monotonic()

                                # Summarize args
                                args_summary = ""
                                if isinstance(tool_input, dict):
                                    # Take first string value as summary
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
                                yield ev

                            elif isinstance(block, ToolResultBlock):
                                # Tool result (error or success)
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
                                yield ev

                            elif isinstance(block, TextBlock):
                                # Text content from assistant
                                text = block.text
                                if text:
                                    last_result_text = text  # Track for recovery
                                    elapsed = int((time.monotonic() - start) * 1000)
                                    ev = {"type": "result", "content": text, "duration_ms": elapsed}
                                    append_event(task_id, ev)
                                    yield ev

                # ResultMessage marks the end of the task
                elif isinstance(message, ResultMessage):
                    # Just acknowledge completion; actual content was in prior TextBlock
                    pass

    except TimeoutError:
        elapsed = int((time.monotonic() - start) * 1000)
        if last_result_text:
            # Recovery: we have a partial result, return it
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
        if last_result_text:
            # Recovery: return captured result despite error
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
