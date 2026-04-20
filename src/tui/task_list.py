from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Tree, Static

from src.storage import list_task_ids, read_events
from src.tui.task_detail import TaskDetailScreen

# Status icons
ICONS = {
    "running": "[yellow]⧖[/]",
    "completed": "[green]✓[/]",
    "error": "[red]✗[/]",
    "queued": "[dim]○[/]",
}


def _task_status(events: list[dict]) -> str:
    """Derive status from events."""
    has_result = any(e["type"] == "result" for e in events)
    has_error = any(e.get("status") == "error" and e["type"] == "tool_end" for e in events)
    if has_result:
        return "completed"
    if has_error:
        return "error"
    if events:
        return "running"
    return "queued"


def _task_label(task_id: str, events: list[dict]) -> str:
    """Build Rich markup label for a task."""
    status = _task_status(events)
    icon = ICONS.get(status, "?")

    # Extract prompt from init event
    prompt = "..."
    for e in events:
        if e["type"] == "init":
            prompt = e.get("prompt", "...")[:50]
            break

    # Duration
    duration = ""
    for e in reversed(events):
        if "duration_ms" in e and e["type"] == "result":
            ms = e["duration_ms"]
            duration = f" [dim]({ms / 1000:.1f}s)[/]"
            break

    # Tool count
    tool_count = sum(1 for e in events if e["type"] == "tool_start")
    tools_info = f" [dim]{tool_count} tools[/]" if tool_count else ""

    return f'{icon} #{task_id} {prompt} [dim]....[/] {status}{tools_info}{duration}'


class TaskListScreen(Screen):
    """Screen B: Task list with Tree widget."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "select_task", "Detail"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Tree("Tasks", id="task-tree")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_tree()
        # Auto-refresh every 2 seconds
        self.set_interval(2.0, self._refresh_tree)

    def _refresh_tree(self) -> None:
        tree: Tree = self.query_one("#task-tree", Tree)
        tree.clear()
        tree.root.expand()

        task_ids = list_task_ids()
        for tid in task_ids:
            events = read_events(tid)
            label = _task_label(tid, events)
            node = tree.root.add_leaf(label)
            node.data = tid  # store task_id for selection

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data:
            self.app.push_screen(TaskDetailScreen(event.node.data))

    def action_refresh(self) -> None:
        self._refresh_tree()

    def action_select_task(self) -> None:
        tree: Tree = self.query_one("#task-tree", Tree)
        if tree.cursor_node and tree.cursor_node.data:
            self.app.push_screen(TaskDetailScreen(tree.cursor_node.data))
