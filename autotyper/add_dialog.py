"""
Add-task dialog for AutoTyper.

Presents a modal dialog where the user can:
- Enter the text to be typed
- Pick a date (Today / Tomorrow / Custom via calendar)
- Set a time (hour + minute spin buttons)
- Toggle whether Enter is pressed after typing

Preconditions:
    - Parent window is a valid Adw.ApplicationWindow

Postconditions:
    - On "Add", a TypingTask is created and added to the TaskStore
    - On "Cancel" or close, nothing happens
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from datetime import datetime, timedelta

from gi.repository import Gtk, Adw, GLib

from .task_model import TaskStore, TypingTask


class AddTaskDialog(Adw.Window):
    """Modal dialog for creating a new typing task."""

    def __init__(self, parent: Adw.ApplicationWindow, store: TaskStore) -> None:
        """Initialize the Add Task dialog.

        Args:
            parent: The parent window (used for transient_for).
            store: The TaskStore to add the new task to.
        """
        super().__init__(
            title="New Task",
            transient_for=parent,
            modal=True,
            default_width=440,
            default_height=580,
        )
        self._store = store
        self._selected_date = datetime.now().date()
        self._date_mode = "today"  # "today" | "tomorrow" | "custom"

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the dialog UI."""
        # --- Toolbar view wraps header + content ---
        toolbar = Adw.ToolbarView()
        self.set_content(toolbar)

        # --- Header bar ---
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda _: self.close())
        header.pack_start(cancel_btn)

        self._add_btn = Gtk.Button(label="Add")
        self._add_btn.add_css_class("suggested-action")
        self._add_btn.connect("clicked", self._on_add_clicked)
        header.pack_end(self._add_btn)

        toolbar.add_top_bar(header)

        # --- Content ---
        scroll = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )
        toolbar.set_content(scroll)

        clamp = Adw.Clamp(maximum_size=400, margin_top=24, margin_bottom=24,
                          margin_start=16, margin_end=16)
        scroll.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(box)

        # --- Text input group (multiline) ---
        text_group = Adw.PreferencesGroup(title="Text to type")
        box.append(text_group)

        text_frame = Gtk.Frame()
        text_frame.add_css_class("card")
        self._text_view = Gtk.TextView(
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
            top_margin=12, bottom_margin=12,
            left_margin=12, right_margin=12,
            height_request=100,
            accepts_tab=False,
        )
        self._text_view.get_buffer().set_text("")
        text_frame.set_child(self._text_view)
        text_group.add(text_frame)

        # --- Date group ---
        date_group = Adw.PreferencesGroup(title="Date")
        box.append(date_group)

        # Toggle buttons row
        date_row = Adw.ActionRow(title="When")
        date_group.add(date_row)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4,
                          valign=Gtk.Align.CENTER)

        self._btn_today = Gtk.ToggleButton(label="Today")
        self._btn_today.set_active(True)
        self._btn_today.add_css_class("flat")
        self._btn_today.connect("toggled", self._on_date_toggled, "today")

        self._btn_tomorrow = Gtk.ToggleButton(label="Tomorrow", group=self._btn_today)
        self._btn_tomorrow.add_css_class("flat")
        self._btn_tomorrow.connect("toggled", self._on_date_toggled, "tomorrow")

        self._btn_custom = Gtk.ToggleButton(group=self._btn_today)
        self._btn_custom.set_icon_name("x-office-calendar-symbolic")
        self._btn_custom.set_tooltip_text("Pick a date")
        self._btn_custom.add_css_class("flat")
        self._btn_custom.connect("toggled", self._on_date_toggled, "custom")

        btn_box.append(self._btn_today)
        btn_box.append(self._btn_tomorrow)
        btn_box.append(self._btn_custom)
        date_row.add_suffix(btn_box)

        # Calendar (hidden by default)
        self._calendar_revealer = Gtk.Revealer(
            transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN,
            reveal_child=False,
        )
        self._calendar = Gtk.Calendar()
        self._calendar.connect("day-selected", self._on_calendar_day_selected)
        self._calendar_revealer.set_child(self._calendar)
        box.append(self._calendar_revealer)

        # --- Time group ---
        time_group = Adw.PreferencesGroup(title="Time")
        box.append(time_group)

        time_row = Adw.ActionRow(title="At")
        time_group.add(time_row)

        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4,
                           valign=Gtk.Align.CENTER)

        now = datetime.now()
        default_hour = (now.hour + 1) % 24

        self._hour_spin = Gtk.SpinButton.new_with_range(0, 23, 1)
        self._hour_spin.set_value(default_hour)
        self._hour_spin.set_width_chars(2)
        self._hour_spin.set_wrap(True)

        colon = Gtk.Label(label=":")

        self._minute_spin = Gtk.SpinButton.new_with_range(0, 59, 1)
        self._minute_spin.set_value(0)
        self._minute_spin.set_width_chars(2)
        self._minute_spin.set_wrap(True)

        time_box.append(self._hour_spin)
        time_box.append(colon)
        time_box.append(self._minute_spin)
        time_row.add_suffix(time_box)

        # --- Enter toggle ---
        enter_group = Adw.PreferencesGroup(title="Options")
        box.append(enter_group)

        self._enter_switch = Adw.SwitchRow(
            title="Press Enter after typing",
            active=True,
        )
        enter_group.add(self._enter_switch)

    def _on_date_toggled(self, button: Gtk.ToggleButton, mode: str) -> None:
        """Handle date toggle button changes.

        Args:
            button: The toggled button.
            mode: One of "today", "tomorrow", "custom".
        """
        if not button.get_active():
            # If custom was deselected by re-clicking, close the calendar
            if mode == "custom":
                self._calendar_revealer.set_reveal_child(False)
            return

        self._date_mode = mode
        now = datetime.now()

        if mode == "today":
            self._selected_date = now.date()
            self._calendar_revealer.set_reveal_child(False)
        elif mode == "tomorrow":
            self._selected_date = (now + timedelta(days=1)).date()
            self._calendar_revealer.set_reveal_child(False)
        elif mode == "custom":
            self._calendar_revealer.set_reveal_child(True)
            self._on_calendar_day_selected(self._calendar)

    def _on_calendar_day_selected(self, calendar: Gtk.Calendar) -> None:
        """Handle calendar date selection.

        Args:
            calendar: The GtkCalendar widget.
        """
        gdate = calendar.get_date()  # GLib.DateTime
        self._selected_date = datetime(
            gdate.get_year(), gdate.get_month(), gdate.get_day_of_month()
        ).date()

    def _on_add_clicked(self, _button: Gtk.Button) -> None:
        """Validate input and add the task to the store."""
        buf = self._text_view.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip()
        if not text:
            self._text_view.add_css_class("error")
            return

        hour = int(self._hour_spin.get_value())
        minute = int(self._minute_spin.get_value())

        scheduled = datetime(
            self._selected_date.year,
            self._selected_date.month,
            self._selected_date.day,
            hour, minute, 0
        )

        if scheduled <= datetime.now():
            # Show a toast-like feedback: add error styling
            self._hour_spin.add_css_class("error")
            self._minute_spin.add_css_class("error")
            return

        task = TypingTask(
            text=text,
            scheduled_time=scheduled,
            press_enter=self._enter_switch.get_active(),
        )
        self._store.add(task)
        self.close()
