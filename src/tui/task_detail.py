from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Tree

from src.storage import read_events

# Status icons
ICONS = {
    "running": "[yellow]⧖[/]",
    "ok": "[green]✓[/]",
    "error": "[red]✗[/]",
    "pending": "[dim]○[/]",
}


def _build_detail_tree(tree: Tree, task_id: str, events: list[dict]) -> None:
    """Populate tree with tool-level detail for a task."""
    tree.clear()

    # Derive task status
    has_result = any(e["type"] == "result" for e in events)
    prompt = "..."
    model = "sonnet"
    for e in events:
        if e["type"] == "init":
            prompt = e.get("prompt", "...")[:60]
            model = e.get("model", "sonnet")
            break

    status_icon = ICONS["ok"] if has_result else ICONS["running"]
    status_text = "completed" if has_result else "running"
    tree.root.set_label(
        f'[bold]Task #{task_id}[/] {status_icon} [italic]{status_text}[/] "{prompt}" [dim]({model})[/]'
    )
    tree.root.expand()

    # Track tool starts to pair with ends
    tool_nodes: dict[str, any] = {}  # tool_id -> tree node
    tool_names: dict[str, str] = {}  # tool_id -> tool name

    for event in events:
        etype = event["type"]

        if etype == "tool_start":
            tool_id = event.get("tool_id", "")
            name = event.get("name", "unknown")
            args = event.get("args", "")
            tool_names[tool_id] = name

            # Show as running until we get tool_end
            args_display = f' "{args}"' if args else ""
            label = f"{ICONS['running']} {name}{args_display}"
            node = tree.root.add(label)
            node.expand()
            tool_nodes[tool_id] = node

        elif etype == "tool_end":
            tool_id = event.get("tool_id", "")
            status = event.get("status", "ok")
            dur = event.get("duration_ms", 0)
            detail = event.get("detail", "")
            name = tool_names.get(tool_id, "unknown")
            icon = ICONS.get(status, "?")

            dur_str = f" [dim]{dur / 1000:.1f}s[/]" if dur else ""

            if tool_id in tool_nodes:
                # Update the existing node label
                node = tool_nodes[tool_id]
                args = ""
                # Recover args from original label
                for e2 in events:
                    if e2.get("tool_id") == tool_id and e2["type"] == "tool_start":
                        args = e2.get("args", "")
                        break
                args_display = f' "{args}"' if args else ""
                node.set_label(f"{icon} {name}{args_display}{dur_str}")

                # Add detail as child
                if detail:
                    detail_short = detail[:120]
                    node.add_leaf(f"[dim]└── {detail_short}[/]")
            else:
                # Orphan tool_end (shouldn't happen, but handle gracefully)
                tree.root.add_leaf(f"{icon} {name}{dur_str}")

        elif etype == "result":
            content = event.get("content", "")[:200]
            dur = event.get("duration_ms", 0)
            dur_str = f" [dim]({dur / 1000:.1f}s total)[/]" if dur else ""
            result_node = tree.root.add(f"[bold green]Result[/]{dur_str}")
            result_node.expand()
            # Wrap result text
            for line in content.split("\n")[:10]:
                if line.strip():
                    result_node.add_leaf(f"[dim]{line.strip()[:100]}[/]")


class TaskDetailScreen(Screen):
    """Screen A: Detailed tool-level view of a single task."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, task_id: str) -> None:
        super().__init__()
        self.task_id = task_id

    def compose(self) -> ComposeResult:
        yield Header()
        yield Tree("Loading...", id="detail-tree")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_tree()
        # Live update every 1 second
        self.set_interval(1.0, self._refresh_tree)

    def _refresh_tree(self) -> None:
        tree: Tree = self.query_one("#detail-tree", Tree)
        events = read_events(self.task_id)
        _build_detail_tree(tree, self.task_id, events)

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_refresh(self) -> None:
        self._refresh_tree()
