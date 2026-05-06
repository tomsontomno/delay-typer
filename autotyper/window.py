"""
Main application window for AutoTyper.

Displays the list of scheduled typing tasks. Provides:
- A header bar with an "Add" button
- Task list with status indicators and delete actions
- Empty state when no tasks exist
- Hides to background on close (app keeps running)

Preconditions:
    - Adw.Application is running
    - TaskStore and Scheduler are initialized

Postconditions:
    - Window is presented with current task list
    - Closing hides the window but keeps the app alive
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio

from .task_model import TaskStore, TaskStatus
from .add_dialog import AddTaskDialog


# Status badge config: (css_class, label)
_STATUS_BADGES: dict[TaskStatus, tuple[str, str]] = {
    TaskStatus.PENDING:   ("accent",  "Pending"),
    TaskStatus.RUNNING:   ("warning", "Running"),
    TaskStatus.DONE:      ("success", "Done"),
    TaskStatus.FAILED:    ("error",   "Failed"),
    TaskStatus.CANCELLED: ("",        "Cancelled"),
}


class AutoTyperWindow(Adw.ApplicationWindow):
    """Main window showing the scheduled task list."""

    def __init__(self, store: TaskStore, **kwargs) -> None:
        """Initialize the main window.

        Args:
            store: The shared TaskStore instance.
            **kwargs: Passed to Adw.ApplicationWindow.
        """
        super().__init__(
            title="Delay Typer",
            default_width=500,
            default_height=750,
            **kwargs,
        )
        self._store = store
        self._store.on_change(self._rebuild_list)

        self._build_ui()
        self._rebuild_list()

        # Hide on close instead of destroying — app stays alive in background
        self.connect("close-request", self._on_close_request)

    def _build_ui(self) -> None:
        """Build the window UI."""
        toolbar = Adw.ToolbarView()
        self.set_content(toolbar)

        # --- Header bar ---
        header = Adw.HeaderBar()

        add_btn = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Add Task")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_add_clicked)
        header.pack_end(add_btn)

        toolbar.add_top_bar(header)

        # --- Content: stack with empty-state and list ---
        self._stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        toolbar.set_content(self._stack)

        # Empty state
        empty = Adw.StatusPage(
            icon_name="preferences-desktop-keyboard-symbolic",
            title="No tasks yet",
            description="Add a task to schedule text typing",
        )
        self._stack.add_named(empty, "empty")

        # Task list
        scroll = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )
        clamp = Adw.Clamp(maximum_size=600, margin_top=16, margin_bottom=16,
                          margin_start=16, margin_end=16)
        scroll.set_child(clamp)

        self._list_box = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE,
            css_classes=["boxed-list"],
        )
        clamp.set_child(self._list_box)

        self._stack.add_named(scroll, "list")

    def _rebuild_list(self) -> None:
        """Rebuild the task list from the store.

        Postcondition: UI reflects the current state of TaskStore.
        """
        # Clear existing rows
        while True:
            row = self._list_box.get_row_at_index(0)
            if row is None:
                break
            self._list_box.remove(row)

        tasks = self._store.get_all()

        if not tasks:
            self._stack.set_visible_child_name("empty")
            return

        self._stack.set_visible_child_name("list")

        for task in tasks:
            css_class, badge_label = _STATUS_BADGES.get(
                task.status, ("", "Unknown")
            )

            row = Adw.ActionRow(
                title=task.text,
                subtitle=task.time_label,
            )

            # Status badge
            badge = Gtk.Label(label=badge_label)
            badge.add_css_class("caption")
            if css_class:
                badge.add_css_class(css_class)
            badge.set_valign(Gtk.Align.CENTER)
            row.add_suffix(badge)

            # Enter indicator
            if task.press_enter:
                enter_icon = Gtk.Image(
                    icon_name="keyboard-enter-symbolic",
                    tooltip_text="Enter will be pressed",
                    opacity=0.5,
                )
                enter_icon.set_valign(Gtk.Align.CENTER)
                row.add_suffix(enter_icon)

            # Action buttons (right side)
            task_id = task.id

            if task.status == TaskStatus.PENDING:
                # Stop button — cancels the task (keeps it in list as Cancelled)
                stop_btn = Gtk.Button(
                    icon_name="media-playback-stop-symbolic",
                    tooltip_text="Cancel task",
                    valign=Gtk.Align.CENTER,
                    css_classes=["flat", "circular"],
                )
                stop_btn.connect(
                    "clicked",
                    lambda _, tid=task_id: self._store.update_status(tid, TaskStatus.CANCELLED),
                )
                row.add_suffix(stop_btn)

            if task.status in (TaskStatus.CANCELLED, TaskStatus.DONE, TaskStatus.FAILED):
                # Trash button — removes the task from the list entirely
                delete_btn = Gtk.Button(
                    icon_name="user-trash-symbolic",
                    tooltip_text="Remove from list",
                    valign=Gtk.Align.CENTER,
                    css_classes=["flat", "circular"],
                )
                delete_btn.connect("clicked", lambda _, tid=task_id: self._store.remove(tid))
                row.add_suffix(delete_btn)

            self._list_box.append(row)


    def _on_add_clicked(self, _button: Gtk.Button) -> None:
        """Open the Add Task dialog."""
        dialog = AddTaskDialog(parent=self, store=self._store)
        dialog.present()

    def _on_close_request(self, _window: Adw.ApplicationWindow) -> bool:
        """Hide the window instead of closing the app.

        Returns:
            True to prevent the default close behavior.
        """
        self.set_visible(False)
        return True
