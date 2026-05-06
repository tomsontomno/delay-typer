<div align="center">
  <img src="data/icons/io.github.delaytyper.png" width="128" height="128" alt="Delay Typer icon"/>
  <h1>Delay Typer</h1>
  <p><strong>Schedule text to be automatically typed into any window — at any time you choose.</strong></p>
  <p>
    <img alt="Platform: Linux" src="https://img.shields.io/badge/platform-Linux-blue?logo=linux&logoColor=white"/>
    <img alt="Wayland" src="https://img.shields.io/badge/Wayland-native-brightgreen?logo=wayland"/>
    <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white"/>
    <img alt="GTK4 + Adwaita" src="https://img.shields.io/badge/GTK4-Adwaita-informational?logo=gnome&logoColor=white"/>
    <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green"/>
  </p>
</div>

---

## What is Delay Typer?

Delay Typer is a native **GNOME desktop application** that lets you schedule text to be automatically typed into any focused window at a specific date and time.

**Real-world use cases:**
- Sending a message at a precise moment without being at the computer
- Automating keyboard input for applications that don't support scripting
- Scheduling form submissions, chat messages, or terminal commands
- Anything that needs "type this, exactly at this time"

It runs **natively on Wayland** (including GNOME on Ubuntu, Fedora, etc.) using `/dev/uinput` directly — no X11 compatibility layer needed.

---

## Features

- **Scheduled typing** — pick a date and time, Delay Typer handles the rest
- **Multiple tasks** — queue as many typing tasks as you need, they run sequentially
- **Wayland-native** — uses `wl-clipboard` + `evdev` `/dev/uinput` instead of the blocked virtual keyboard protocol
- **Multiline text** — type paragraphs, not just single lines
- **Optional Enter key** — toggle whether Enter is pressed after the text
- **Smart date shortcuts** — Today / Tomorrow / custom calendar picker
- **Background operation** — closing the window keeps the app running; scheduled tasks still fire
- **Single-instance** — re-launching focuses the existing window instead of opening a duplicate
- **Sequential execution** — concurrent tasks are serialized to avoid clipboard race conditions
- **GNOME-native UI** — built with GTK4 + Libadwaita, follows your system theme

---

## Screenshots

> *Add a task, close the window, walk away. Delay Typer will type your text exactly when you told it to.*

---

## Requirements

| Dependency | Purpose |
|---|---|
| Python 3.10+ | Runtime |
| `python3-gi` (PyGObject) | GTK4 / Adwaita bindings |
| `python3-evdev` | `/dev/uinput` keyboard injection |
| `wl-clipboard` (`wl-copy`, `wl-paste`) | Clipboard-based text paste on Wayland |
| GTK 4.0 + Libadwaita 1.0 | UI framework |

**User must be in the `input` group** to access `/dev/uinput`:
```bash
groups  # check if 'input' is listed
```
If not:
```bash
sudo usermod -aG input $USER  # then log out and back in
```

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/tomsontomno/delay-typer.git
cd delay-typer
```

### 2. Install system dependencies

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
                 python3-evdev wl-clipboard
```

### 3. Install the desktop launcher

```bash
cp data/autotyper.desktop ~/.local/share/applications/delay-typer.desktop
update-desktop-database ~/.local/share/applications/
```

Edit the `Exec=` line in the copied `.desktop` file to point to the full path of `run.py` if you moved the project.

### 4. Run

```bash
python3 run.py
```

Or find **Delay Typer** in your GNOME Activities search.

---

## How it works

Wayland's security model blocks applications from injecting keyboard input via the virtual keyboard protocol (you'll see: `Compositor does not support the virtual keyboard protocol`).

Delay Typer works around this cleanly:

1. **Clipboard paste approach**: text is placed on the Wayland clipboard via `wl-copy`
2. **`/dev/uinput` injection**: `evdev` synthesizes a `Ctrl+V` keystroke to paste it
3. **Sequential lock**: a `threading.Lock` ensures concurrent tasks don't race on the clipboard
4. **Clipboard restore**: the original clipboard content is restored after pasting

This works with any keyboard layout and supports full Unicode text.

```
Task fires
    │
    ├─ Save clipboard (wl-paste)
    ├─ Set clipboard to task text (wl-copy)
    ├─ Synthesize Ctrl+V via /dev/uinput
    ├─ Optionally synthesize Enter
    └─ Restore original clipboard (wl-copy)
```

---

## Project structure

```
delay-typer/
├── run.py                  # Entry point
├── autotyper/
│   ├── main.py             # Adw.Application, app lifecycle
│   ├── window.py           # Main window, task list UI
│   ├── add_dialog.py       # Add-task modal dialog
│   ├── task_model.py       # TypingTask dataclass + TaskStore
│   ├── scheduler.py        # Background GLib-integrated scheduler
│   └── typer.py            # Wayland typing engine (evdev + wl-clipboard)
└── data/
    ├── autotyper.desktop   # .desktop launcher file
    └── icons/
        └── io.github.delaytyper.png
```

---

## Usage

1. **Open Delay Typer** from Activities or `python3 run.py`
2. **Click +** (top right) to add a new task
3. **Enter your text** (multiline supported)
4. **Pick when**: Today, Tomorrow, or a specific date via the calendar
5. **Set the time** with the hour and minute spinners
6. **Toggle Enter** if you want Enter pressed after the text
7. **Click Add** — the task appears in the list with a "Pending" badge
8. **Close the window** — the app keeps running in the background
9. At the scheduled time, the text is typed into whatever window is focused

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first.

---

## License

MIT — see [LICENSE](LICENSE) for details.
