"""
Typing engine for Wayland.

Uses wl-clipboard (wl-copy/wl-paste) + evdev UInput to reliably type text
into any focused window. The clipboard approach bypasses keyboard layout
issues entirely — works with QWERTZ, QWERTY, Dvorak, etc.

Preconditions:
    - User is in the 'input' group (access to /dev/uinput)
    - wl-copy and wl-paste are installed (wl-clipboard package)
    - A Wayland compositor is running

Postconditions:
    - The target text appears in the currently focused window
    - The original clipboard content is restored
"""

import subprocess
import time
from typing import Optional

from evdev import UInput, ecodes as e


def _save_clipboard() -> Optional[str]:
    """Save the current clipboard content.

    Returns:
        The clipboard text, or None if clipboard is empty/inaccessible.
    """
    try:
        result = subprocess.run(
            ['wl-paste', '--no-newline'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _restore_clipboard(content: Optional[str]) -> None:
    """Restore clipboard to previous content.

    Args:
        content: The text to restore, or None to skip.
    """
    if content is None:
        return
    try:
        subprocess.run(
            ['wl-copy', '--', content],
            timeout=2, check=False
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


def _set_clipboard(text: str) -> bool:
    """Set clipboard to the given text.

    Args:
        text: The text to place on the clipboard.

    Returns:
        True if successful, False otherwise.
    """
    try:
        result = subprocess.run(
            ['wl-copy', '--', text],
            timeout=2, check=False
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def type_text(text: str, press_enter: bool = True) -> bool:
    """Type text into the currently focused window via clipboard paste.

    Saves the current clipboard, sets it to the target text, presses Ctrl+V,
    optionally presses Enter, then restores the original clipboard.

    Args:
        text: The text to type.
        press_enter: If True, press Enter after pasting.

    Returns:
        True if the operation succeeded, False otherwise.

    Preconditions:
        - /dev/uinput is accessible (user in 'input' group)
        - A window is focused in the Wayland compositor

    Postconditions:
        - The text has been pasted into the focused window
        - Enter has been pressed if press_enter is True
        - The original clipboard content has been restored
    """
    original_clipboard = _save_clipboard()

    if not _set_clipboard(text):
        return False

    time.sleep(0.15)

    try:
        with UInput() as ui:
            time.sleep(0.3)

            # Ctrl+V (paste)
            ui.write(e.EV_KEY, e.KEY_LEFTCTRL, 1)
            ui.syn()
            time.sleep(0.02)
            ui.write(e.EV_KEY, e.KEY_V, 1)
            ui.syn()
            time.sleep(0.05)
            ui.write(e.EV_KEY, e.KEY_V, 0)
            ui.syn()
            time.sleep(0.02)
            ui.write(e.EV_KEY, e.KEY_LEFTCTRL, 0)
            ui.syn()

            time.sleep(0.15)

            if press_enter:
                ui.write(e.EV_KEY, e.KEY_ENTER, 1)
                ui.syn()
                time.sleep(0.05)
                ui.write(e.EV_KEY, e.KEY_ENTER, 0)
                ui.syn()

            time.sleep(0.2)

    except PermissionError:
        _restore_clipboard(original_clipboard)
        return False

    _restore_clipboard(original_clipboard)
    return True
