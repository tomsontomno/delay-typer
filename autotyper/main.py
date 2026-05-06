"""
Delay Typer — Entry point.

Starts the Adwaita application, initializes the TaskStore and Scheduler,
and keeps the app alive in the background even when the window is closed.

Usage:
    python3 -m autotyper
    # or
    python3 /path/to/AutoTyper/run.py
"""

import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gio, GLib, GdkPixbuf

from .task_model import TaskStore
from .scheduler import Scheduler
from .window import AutoTyperWindow


# Icon path: relative to this file → data/icons/io.github.delaytyper.png
_ICON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "icons", "io.github.delaytyper.png"
)


class AutoTyperApp(Adw.Application):
    """Main Adwaita application.

    Manages the single window instance, task store, and background scheduler.
    The app stays alive when the window is hidden (via Gio.Application.hold).
    Re-launching activates the existing instance and re-shows the window.
    """

    def __init__(self) -> None:
        super().__init__(
            application_id="io.github.delaytyper",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        # Set app icon for taskbar / app switcher
        if os.path.exists(_ICON_PATH):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(_ICON_PATH)
                Gtk = __import__('gi.repository', fromlist=['Gtk']).Gtk
                Gtk.Window.set_default_icon(pixbuf)
            except Exception:
                pass
        self._store = TaskStore()
        self._scheduler = Scheduler(self._store)
        self._window: AutoTyperWindow | None = None

    def do_activate(self) -> None:
        """Show the window (create if first launch, re-show if hidden)."""
        if self._window is None:
            self._window = AutoTyperWindow(
                store=self._store,
                application=self,
                title="Delay Typer",
            )
            # Hold keeps the app alive when the window is hidden
            self.hold()
            # Start the background scheduler
            self._scheduler.start()

        self._window.set_visible(True)
        self._window.present()

    def do_shutdown(self) -> None:
        """Clean up the scheduler on exit."""
        self._scheduler.stop()
        Adw.Application.do_shutdown(self)


def main() -> None:
    """Application entry point."""
    app = AutoTyperApp()
    app.run(None)
