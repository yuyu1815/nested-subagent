# nested-subagent

Python MCP server that runs nested Claude subagents via the Claude Agent SDK.

Exposes a single `task` tool through FastMCP — delegate work to a subagent with full tool access, session resume, and cost tracking.

## Features

- **Full tool access** — Subagents run with the complete Claude Code toolset (Read, Edit, Bash, Grep, etc.)
- **Session resume** — Continue a previous conversation by passing back the `session_id`
- **Cost tracking** — Each task returns `cost_usd` for budget management
- **Timeout + error recovery** — Configurable timeout with partial result recovery
- **Debug logging** — All operations logged to `.claude/debug.log`
- **JSONL event stream** — Tool usage and results persisted to `.claude/tasks/`

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/yuyu1815/nested-subagent.git
cd nested-subagent
uv sync
```

### Register as MCP server

Add to your Claude Code project's `.mcp.json`:

```json
{
  "mcpServers": {
    "nested-subagent": {
      "command": "uv",
      "args": ["run", "python", "-m", "src.server"],
      "cwd": "/path/to/nested-subagent"
    }
  }
}
```

## Usage

Once registered, the `mcp__nested_subagent__task` tool is available in Claude Code:

```
prompt: "Read pyproject.toml and list the dependencies"
model: "haiku"
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | string | *required* | Task for the agent |
| `model` | string | `sonnet` | `sonnet`, `opus`, or `haiku` |
| `cwd` | string | — | Working directory |
| `session_id` | string | — | Resume a previous session |
| `system_prompt` | string | — | Custom system prompt (overrides default) |
| `allowed_tools` | string[] | — | Tools to allow |
| `disallowed_tools` | string[] | — | Tools to disallow |
| `max_budget_usd` | number | — | Cost limit in USD |
| `timeout` | number | `600000` | Timeout in milliseconds |

### Return format

```json
{
  "result": "Task output text",
  "session_id": "abc123-...",
  "cost_usd": 0.0042
}
```

Pass `session_id` back to continue the conversation:

```
prompt: "Now refactor that function"
session_id: "abc123-..."
```

## Architecture

```
Claude Code (host)
  └── MCP tool call
       └── server.py (FastMCP)
            └── runner.py
                 ├── Claude Agent SDK query()
                 ├── Events → .claude/tasks/*.jsonl
                 └── Debug  → .claude/debug.log
```

| File | Role |
|------|------|
| `src/server.py` | MCP server, tool definition, result collection |
| `src/runner.py` | Agent execution, event streaming, error recovery |
| `src/storage.py` | JSONL event persistence |
| `src/tui/` | Textual TUI viewer for real-time monitoring |

## License

MIT
