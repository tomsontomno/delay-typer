"""
Background scheduler for AutoTyper.

Runs on the GLib main loop via GLib.timeout_add_seconds.
Checks the TaskStore every second for due tasks and fires them
in a background thread to avoid blocking the UI.

Preconditions:
    - A GLib main loop is running (provided by Gtk.Application)
    - The TaskStore is populated with tasks

Postconditions:
    - Due tasks are executed (text typed into the focused window)
    - Task statuses are updated in the store
"""

import threading
from typing import TYPE_CHECKING

from gi.repository import GLib

from .task_model import TaskStatus
from .typer import type_text

if TYPE_CHECKING:
    from .task_model import TaskStore, TypingTask


class Scheduler:
    """Polls the TaskStore and fires due tasks.

    Uses GLib.timeout_add_seconds for integration with the GTK main loop.
    Each task is executed in a daemon thread so the UI stays responsive.

    Invariant: Only one Scheduler instance should run per application.
    """

    def __init__(self, store: "TaskStore") -> None:
        """Initialize the scheduler.

        Args:
            store: The TaskStore to poll for due tasks.
        """
        self._store = store
        self._source_id: int | None = None
        self._type_lock = threading.Lock()  # serialize clipboard access

    def start(self) -> None:
        """Start polling every second.

        Precondition: GLib main loop is running.
        Postcondition: _check_tasks is called every second.
        """
        if self._source_id is not None:
            return
        self._source_id = GLib.timeout_add_seconds(1, self._check_tasks)

    def stop(self) -> None:
        """Stop polling.

        Postcondition: No more periodic checks are scheduled.
        """
        if self._source_id is not None:
            GLib.source_remove(self._source_id)
            self._source_id = None

    def _check_tasks(self) -> bool:
        """Check for due tasks and fire them.

        Returns:
            True to keep the timeout alive.
        """
        due = self._store.get_due_tasks()
        for task in due:
            self._store.update_status(task.id, TaskStatus.RUNNING)
            self._fire_in_thread(task)
        return True  # keep the timeout running

    def _fire_in_thread(self, task: "TypingTask") -> None:
        """Execute a task's typing in a background thread.

        Args:
            task: The task to execute.

        Postcondition: task status is updated to DONE or FAILED.
        """
        def _run() -> None:
            with self._type_lock:  # only one task pastes at a time
                success = type_text(task.text, task.press_enter)
            new_status = TaskStatus.DONE if success else TaskStatus.FAILED
            GLib.idle_add(self._store.update_status, task.id, new_status)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
