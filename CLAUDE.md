# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python MCP server that runs nested Claude subagents via the Claude Agent SDK. Exposes a single `task` tool through FastMCP that executes delegated tasks with full tool access.

Design influenced by [heyinc/kuro](https://github.com/heyinc/kuro) — a production Claude agent system for STORES.

## Commands

```bash
uv run python -m src.server          # Run MCP server (stdio transport)
uv run python -m py_compile src/runner.py  # Syntax check
uv run python -m py_compile src/server.py  # Syntax check
```

### MCP Registration (`.mcp.json`)

```json
{
  "mcpServers": {
    "nested-subagent": {
      "command": "uv",
      "args": ["run", "python", "-m", "src.server"],
      "cwd": "."
    }
  }
}
```

After code changes, reconnect with `/mcp` in Claude Code.

## Architecture

```
Claude Code (host)
  └── MCP tool call ──→ server.py (FastMCP)
       └── run_task() ──→ runner.py
            ├── ClaudeAgentOptions (bypassPermissions, preset+append)
            ├── query() ──→ Claude Agent SDK
            │    ├── AssistantMessage → tool_start/tool_end/result events
            │    └── ResultMessage → session_id, cost_usd
            ├── Events → JSONL (.claude/tasks/)
            ├── Events → TUI viewer (Textual)
            └── Debug → .claude/debug.log
```

### Key Design Decisions

- **Same-process execution**: Unlike kuro (child process spawn), we call `query()` directly. Simpler, sufficient for CLI plugin use case.
- **bypassPermissions hardcoded**: Subagents must not prompt for permission — the host agent handles authorization.
- **Preset system prompt with append**: Uses `claude_code` preset to retain full tool access, appends response rules to control output format.
- **Error recovery**: If a partial result was captured before an error/timeout, return it instead of failing (kuro pattern).

## Directory Structure

```
nested-subagent/
├── .mcp.json              # MCP server configuration
├── .claude/
│   ├── tasks/             # JSONL event logs per task (gitignored)
│   └── debug.log          # Debug log (gitignored)
├── src/
│   ├── server.py          # FastMCP server, task tool definition
│   ├── runner.py          # Agent execution via Claude Agent SDK query()
│   ├── storage.py         # JSONL persistence
│   ├── models.py          # Data models (TaskStatus, ToolEvent, etc.)
│   └── tui/
│       ├── app.py         # Textual TUI main app
│       ├── task_list.py   # Task list widget
│       └── task_detail.py # Task detail widget
├── pyproject.toml         # Python project config (uv)
└── CLAUDE.md              # This file
```

## Key Files

| File | Role |
|------|------|
| `src/server.py` | FastMCP server. Defines `task` tool, launches TUI, collects results. Returns JSON with result + session_id + cost. |
| `src/runner.py` | Core execution. Builds ClaudeAgentOptions, calls `query()`, yields structured events. Contains `SUBAGENT_PROMPT_APPEND`. |
| `src/storage.py` | Appends events to `.claude/tasks/{task_id}.jsonl`. |

## Tool Parameters

The `mcp__nested_subagent__task` tool accepts:

| Parameter | Type | Description |
|-----------|------|-------------|
| `prompt` | string | **Required.** Task for the agent |
| `model` | string | `sonnet`, `opus`, or `haiku` *(Default: `sonnet`)* |
| `cwd` | string | Working directory for the agent |
| `session_id` | string | Session ID for resuming a previous conversation |
| `system_prompt` | string | Custom system prompt (overrides preset+append) |
| `allowed_tools` | string[] | Tools to allow |
| `disallowed_tools` | string[] | Tools to disallow |
| `max_budget_usd` | number | Cost limit in USD |
| `timeout` | number | Timeout in milliseconds *(Default: `600000`)* |

### Return Format

```json
{
  "result": "Task output text",
  "session_id": "abc123-...",
  "cost_usd": 0.0042
}
```

`session_id` can be passed back to resume the conversation.

## Debug Logging

All operations log to `.claude/debug.log`:

```
[timestamp] [server] task called: task_id=535c086a model=haiku prompt=...
[timestamp] [runner] run_task start: task_id=535c086a model=haiku cwd=None
[timestamp] [runner] options built: ['model', 'permission_mode', 'system_prompt']
[timestamp] [runner] query() starting
[timestamp] [runner] result: 1 chars, 4352ms
[timestamp] [runner] ResultMessage: session_id=... cost_usd=0.0042
[timestamp] [server] task 535c086a done: 1 chars
```

## Dependencies

- `claude-agent-sdk>=0.1.63` — Agent execution
- `fastmcp>=3.2.4` — MCP server framework
- `textual>=8.2.4` — TUI viewer
- `watchfiles>=1.1.1` — File watching for TUI
