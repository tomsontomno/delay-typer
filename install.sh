#!/usr/bin/env bash
# install.sh — Delay Typer one-command installer
#
# Usage:
#   bash <(curl -fsSL https://raw.githubusercontent.com/tomsontomno/delay-typer/main/install.sh)
#
# What this does:
#   1. Installs system dependencies via apt
#   2. Clones the repo to ~/.local/share/delay-typer
#   3. Ensures you are in the 'input' group
#   4. Installs the .desktop launcher
#   5. Sets up a convenient 'delay-typer' command in PATH

set -euo pipefail

REPO_URL="https://github.com/tomsontomno/delay-typer.git"
INSTALL_DIR="$HOME/.local/share/delay-typer"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

# ---- Colors ----
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[delay-typer]${NC} $*"; }
warning() { echo -e "${YELLOW}[delay-typer]${NC} $*"; }
error()   { echo -e "${RED}[delay-typer] ERROR:${NC} $*" >&2; exit 1; }

echo ""
echo "  Delay Typer -- Installer"
echo "  ================================"
echo ""

# ---- Check OS ----
if ! command -v apt-get &>/dev/null; then
  error "This installer requires apt (Debian/Ubuntu). For other distros, see README.md."
fi

# ---- Install system dependencies ----
info "Installing system dependencies..."
sudo apt-get install -y -q \
  python3 \
  python3-gi \
  python3-gi-cairo \
  gir1.2-gtk-4.0 \
  gir1.2-adw-1 \
  python3-evdev \
  wl-clipboard \
  git 2>&1 | grep -E "^(Get|Setting|Unpacking|Reading)" || true
info "Dependencies installed."

# ---- Check /dev/uinput access ----
if ! groups | grep -qw input; then
  warning "You are not in the 'input' group. Adding you now..."
  sudo usermod -aG input "$USER"
  warning "You need to LOG OUT and back in for this to take effect."
  warning "After re-login, run: delay-typer"
fi

# Fix /dev/uinput permissions for current session (until next reboot)
if [ -e /dev/uinput ]; then
  sudo chmod 660 /dev/uinput
  sudo chown root:input /dev/uinput 2>/dev/null || true
fi

# ---- Clone or update repo ----
if [ -d "$INSTALL_DIR/.git" ]; then
  info "Updating existing installation at $INSTALL_DIR ..."
  git -C "$INSTALL_DIR" pull --ff-only
else
  info "Cloning to $INSTALL_DIR ..."
  git clone --depth=1 "$REPO_URL" "$INSTALL_DIR"
fi

# ---- Install icon ----
mkdir -p "$ICON_DIR"
cp "$INSTALL_DIR/data/icons/io.github.delaytyper.png" \
   "$ICON_DIR/io.github.delaytyper.png"

# ---- Install .desktop launcher ----
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/io.github.delaytyper.desktop" << EOF
[Desktop Entry]
Name=Delay Typer
GenericName=Scheduled Text Typer
Comment=Schedule text to be typed automatically at a specific date and time
Exec=python3 $INSTALL_DIR/run.py
Icon=io.github.delaytyper
Type=Application
Categories=Utility;Accessibility;
Keywords=type;typing;schedule;timer;keyboard;automation;
StartupNotify=true
SingleMainWindow=true
EOF

update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

# ---- Install CLI command ----
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/delay-typer" << EOF
#!/usr/bin/env bash
exec python3 "$INSTALL_DIR/run.py" "\$@"
EOF
chmod +x "$BIN_DIR/delay-typer"

# Ensure ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  warning "$BIN_DIR is not in your PATH."
  warning "Add this to your ~/.bashrc or ~/.zshrc:"
  warning "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
info "Delay Typer installed successfully!"
echo ""
echo "  Run from terminal:  delay-typer"
echo "  Or search 'Delay Typer' in GNOME Activities"
echo ""
if ! groups | grep -qw input; then
  warning "Remember: log out and back in before first use (input group change)."
fi
