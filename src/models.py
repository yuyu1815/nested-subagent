from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class ToolStatus(str, Enum):
    RUNNING = "running"
    OK = "ok"
    ERROR = "error"


@dataclass
class ToolEvent:
    """Single tool invocation within a task."""
    name: str
    status: ToolStatus
    args: str = ""
    detail: str = ""
    duration_ms: int = 0


@dataclass
class TaskSummary:
    """Lightweight task info for list view."""
    id: str
    prompt: str
    model: str
    status: TaskStatus = TaskStatus.QUEUED
    tool_count: int = 0
    duration_ms: int = 0
