#!/bin/bash
# Installation script for Git Profile Switcher tray icon application

set -e

echo "Installing Git Profile Switcher tray icon application..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please do not run as root. This script installs to your home directory."
    exit 1
fi

# Install system dependencies
echo "Checking for required system packages..."

# Check for Fedora/RHEL
if command -v dnf &> /dev/null; then
    echo "Detected Fedora/RHEL system"
    echo "Installing required packages (sudo required)..."
    sudo dnf install -y python3-gobject libappindicator-gtk3
elif command -v apt-get &> /dev/null; then
    echo "Detected Debian/Ubuntu system"
    echo "Installing required packages (sudo required)..."
    sudo apt-get update
    sudo apt-get install -y python3-gi gir1.2-appindicator3-0.1
else
    echo "WARNING: Could not detect package manager."
    echo "Please ensure you have: python3-gobject and libappindicator-gtk3 installed"
fi

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Install desktop entry
mkdir -p "$HOME/.local/share/applications"
sed "s|python3 -m gps.tray|python3 \"$SCRIPT_DIR\"|g" "$SCRIPT_DIR/git-profile-switcher-tray.desktop" > "$HOME/.local/share/applications/git-profile-switcher-tray.desktop"
chmod +x "$HOME/.local/share/applications/git-profile-switcher-tray.desktop"

# Install icon (create a simple SVG icon if not present)
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
mkdir -p "$ICON_DIR"

if [ ! -f "$ICON_DIR/git-profile-switcher.svg" ]; then
    echo "Creating icon..."
    cat > "$ICON_DIR/git-profile-switcher.svg" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <circle cx="32" cy="32" r="30" fill="#f05032"/>
  <path d="M 20 32 L 28 40 L 44 24" stroke="white" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <text x="32" y="52" font-family="sans-serif" font-size="8" text-anchor="middle" fill="white">Git</text>
</svg>
EOF
fi

# Update desktop database
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo ""
echo "Installation complete!"
echo ""
echo "To start the application, run:"
echo "  python3 main.py"
echo ""
echo "Or launch from your application menu."
echo ""
echo "To enable autostart on login:"
echo "  ln -s \"$HOME/.local/share/applications/git-profile-switcher-tray.desktop\" \"$HOME/.config/autostart/\""
echo ""
