"""
Task model for AutoTyper.

Defines the TypingTask dataclass and the TaskStore that manages the
in-memory list of scheduled tasks.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional


class TaskStatus(Enum):
    """Lifecycle states of a typing task."""
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TypingTask:
    """A scheduled text-typing task.

    Attributes:
        id: Unique identifier.
        text: The text to type.
        scheduled_time: When to fire.
        press_enter: Whether to press Enter after typing.
        status: Current lifecycle state.
    """
    text: str
    scheduled_time: datetime
    press_enter: bool = True
    status: TaskStatus = TaskStatus.PENDING
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    @property
    def is_due(self) -> bool:
        """Check if this task should fire now.

        Returns:
            True if the task is pending and the scheduled time has passed.
        """
        return (
            self.status == TaskStatus.PENDING
            and datetime.now() >= self.scheduled_time
        )

    @property
    def time_label(self) -> str:
        """Human-readable label for the scheduled time.

        Returns:
            A string like "Today at 14:30" or "06 May at 09:00".
        """
        now = datetime.now()
        if self.scheduled_time.date() == now.date():
            day = "Today"
        elif (self.scheduled_time.date() - now.date()).days == 1:
            day = "Tomorrow"
        else:
            day = self.scheduled_time.strftime("%d %b")
        return f"{day} at {self.scheduled_time.strftime('%H:%M')}"


class TaskStore:
    """In-memory store for typing tasks.

    Provides add/remove/query operations and notifies listeners on changes.

    Invariant: Each task has a unique id within the store.
    """

    def __init__(self) -> None:
        self._tasks: list[TypingTask] = []
        self._listeners: list[Callable[[], None]] = []

    def add(self, task: TypingTask) -> None:
        """Add a task to the store and notify listeners.

        Args:
            task: The task to add.

        Postcondition: task is in self._tasks, listeners are notified.
        """
        self._tasks.append(task)
        self._notify()

    def remove(self, task_id: str) -> None:
        """Remove a task by id and notify listeners.

        Args:
            task_id: The id of the task to remove.

        Postcondition: task with task_id is no longer in self._tasks.
        """
        self._tasks = [t for t in self._tasks if t.id != task_id]
        self._notify()

    def get_due_tasks(self) -> list[TypingTask]:
        """Return all tasks that are due now.

        Returns:
            List of tasks where is_due is True.
        """
        return [t for t in self._tasks if t.is_due]

    def get_all(self) -> list[TypingTask]:
        """Return all tasks, sorted by scheduled time.

        Returns:
            All tasks in chronological order.
        """
        return sorted(self._tasks, key=lambda t: t.scheduled_time)

    def on_change(self, callback: Callable[[], None]) -> None:
        """Register a listener for store changes.

        Args:
            callback: Called (with no arguments) whenever the store changes.
        """
        self._listeners.append(callback)

    def update_status(self, task_id: str, status: TaskStatus) -> None:
        """Update a task's status and notify listeners.

        Args:
            task_id: The id of the task to update.
            status: The new status.

        Postcondition: task.status == status, listeners are notified.
        """
        for task in self._tasks:
            if task.id == task_id:
                task.status = status
                break
        self._notify()

    def _notify(self) -> None:
        """Notify all registered listeners."""
        for listener in self._listeners:
            listener()
