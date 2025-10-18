#!/bin/bash
set -e

# xSwarm Boss Installation Script
# For static binary distributions

VERSION="0.1.0"
INSTALL_DIR="/usr/local/bin"
DOCS_DIR="/usr/local/share/xswarm/docs"
SYSTEMD_SYSTEM_DIR="/etc/systemd/system"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect architecture
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        ARCH="x86_64"
        ;;
    aarch64|arm64)
        ARCH="aarch64"
        ;;
    *)
        echo -e "${RED}Error: Unsupported architecture: $ARCH${NC}"
        exit 1
        ;;
esac

echo "xSwarm Boss Installer v$VERSION"
echo "================================"
echo ""

# Check for root/sudo
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Warning: Running as root. Will install system-wide.${NC}"
    SYSTEM_INSTALL=true
else
    echo "Running as user. Will install to $HOME/.local/bin"
    INSTALL_DIR="$HOME/.local/bin"
    DOCS_DIR="$HOME/.local/share/xswarm/docs"
    SYSTEM_INSTALL=false
fi

# Create installation directories
echo "Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$DOCS_DIR"

if [ "$SYSTEM_INSTALL" = true ]; then
    mkdir -p /var/lib/xswarm
    mkdir -p /var/log/xswarm
fi

# Install binary
echo "Installing xswarm binary..."
if [ -f "xswarm" ]; then
    install -m 755 xswarm "$INSTALL_DIR/xswarm"
    echo -e "${GREEN}✓${NC} Binary installed to $INSTALL_DIR/xswarm"
else
    echo -e "${RED}Error: xswarm binary not found in current directory${NC}"
    exit 1
fi

# Install documentation
echo "Installing documentation..."
if [ -d "docs" ]; then
    cp -r docs/* "$DOCS_DIR/"
    echo -e "${GREEN}✓${NC} Documentation installed to $DOCS_DIR"
else
    echo -e "${YELLOW}Warning: docs/ directory not found, skipping documentation${NC}"
fi

# Install systemd service (system-wide only)
if [ "$SYSTEM_INSTALL" = true ]; then
    if [ -f "xswarm.service" ]; then
        echo "Installing systemd service..."
        cp xswarm.service "$SYSTEMD_SYSTEM_DIR/xswarm.service"

        # Create xswarm user and group
        if ! getent group xswarm >/dev/null; then
            groupadd -r xswarm
        fi

        if ! getent passwd xswarm >/dev/null; then
            useradd -r -g xswarm -d /var/lib/xswarm -s /usr/sbin/nologin xswarm
        fi

        # Set ownership
        chown -R xswarm:xswarm /var/lib/xswarm
        chown -R xswarm:xswarm /var/log/xswarm

        # Reload systemd
        systemctl daemon-reload

        echo -e "${GREEN}✓${NC} Systemd service installed"
    fi
else
    # User install - offer systemd user service
    if [ -f "xswarm.service" ]; then
        echo "Installing systemd user service..."
        mkdir -p "$SYSTEMD_USER_DIR"

        # Modify service for user install
        sed 's|/usr/bin/xswarm|'"$INSTALL_DIR"'/xswarm|g' xswarm.service > "$SYSTEMD_USER_DIR/xswarm.service"
        sed -i 's|User=xswarm||g' "$SYSTEMD_USER_DIR/xswarm.service"
        sed -i 's|Group=xswarm||g' "$SYSTEMD_USER_DIR/xswarm.service"

        systemctl --user daemon-reload

        echo -e "${GREEN}✓${NC} Systemd user service installed"
    fi
fi

# Add to PATH if needed
if [ "$SYSTEM_INSTALL" = false ]; then
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        echo ""
        echo -e "${YELLOW}Note: $INSTALL_DIR is not in your PATH${NC}"
        echo "Add this line to your shell config (~/.bashrc or ~/.zshrc):"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
fi

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""

# Print next steps
if [ "$SYSTEM_INSTALL" = true ]; then
    echo "To start the xSwarm daemon:"
    echo "  sudo systemctl start xswarm"
    echo ""
    echo "To enable on boot:"
    echo "  sudo systemctl enable xswarm"
    echo ""
    echo "To check status:"
    echo "  sudo systemctl status xswarm"
else
    echo "To start the xSwarm daemon (user service):"
    echo "  systemctl --user start xswarm"
    echo ""
    echo "To enable on login:"
    echo "  systemctl --user enable xswarm"
    echo ""
    echo "To check status:"
    echo "  systemctl --user status xswarm"
fi

echo ""
echo "To use xSwarm CLI:"
echo "  xswarm --help"
echo "  xswarm dashboard"
echo "  xswarm ask \"what's failing?\""
echo ""
echo "Documentation: https://xswarm.dev/docs"
echo ""
