from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding

from src.tui.task_list import TaskListScreen


class AgentViewerApp(App):
    """TUI viewer for nested subagent tasks."""

    TITLE = "Nested Subagent Viewer"
    CSS = """
    Screen {
        background: $surface;
    }
    Tree {
        padding: 1 2;
    }
    #status-bar {
        dock: bottom;
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 2;
    }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        self.push_screen(TaskListScreen())


def main() -> None:
    app = AgentViewerApp()
    app.run()


if __name__ == "__main__":
    main()
