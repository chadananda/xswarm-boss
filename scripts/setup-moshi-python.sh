#!/bin/bash
#
# MOSHI Voice Model - ARM64 Python Setup Script
#
# This script sets up native ARM64 Python for MOSHI on Apple Silicon Macs.
# Requires: macOS 11.0+ on Apple Silicon, sudo access
#
# Usage: sudo bash scripts/setup-moshi-python.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if running on Apple Silicon
check_architecture() {
    info "Checking system architecture..."

    ARCH=$(uname -m)
    if [ "$ARCH" != "arm64" ]; then
        error "This script requires Apple Silicon (ARM64 architecture)"
        error "Detected: $ARCH"
        exit 1
    fi

    success "Running on Apple Silicon ($ARCH)"
}

# Check macOS version
check_macos_version() {
    info "Checking macOS version..."

    MACOS_VERSION=$(sw_vers -productVersion)
    MACOS_MAJOR=$(echo "$MACOS_VERSION" | cut -d. -f1)

    if [ "$MACOS_MAJOR" -lt 11 ]; then
        error "macOS 11.0 or later required (detected: $MACOS_VERSION)"
        exit 1
    fi

    success "macOS $MACOS_VERSION"
}

# Check if script is run with sudo
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        error "This script must be run with sudo"
        echo "Usage: sudo bash scripts/setup-moshi-python.sh"
        exit 1
    fi

    # Get the actual user (not root)
    ACTUAL_USER="${SUDO_USER:-$USER}"
    ACTUAL_HOME=$(eval echo "~$ACTUAL_USER")

    success "Running with admin privileges (user: $ACTUAL_USER)"
}

# Find or install ARM64 Homebrew
setup_homebrew() {
    info "Checking Homebrew installation..."

    # Check if ARM64 Homebrew exists
    if [ -f "/opt/homebrew/bin/brew" ]; then
        success "ARM64 Homebrew already installed at /opt/homebrew"
        BREW_PATH="/opt/homebrew/bin/brew"
        return 0
    fi

    warning "ARM64 Homebrew not found at /opt/homebrew"
    info "Installing ARM64 Homebrew..."

    # Create /opt/homebrew directory
    mkdir -p /opt/homebrew
    chown -R "$ACTUAL_USER:staff" /opt/homebrew

    # Install Homebrew as the actual user (not root)
    su - "$ACTUAL_USER" -c 'arch -arm64 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'

    if [ -f "/opt/homebrew/bin/brew" ]; then
        success "ARM64 Homebrew installed successfully"
        BREW_PATH="/opt/homebrew/bin/brew"

        # Add to user's shell profile
        SHELL_PROFILE="$ACTUAL_HOME/.zprofile"
        if ! grep -q "/opt/homebrew/bin/brew shellenv" "$SHELL_PROFILE" 2>/dev/null; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$SHELL_PROFILE"
            chown "$ACTUAL_USER:staff" "$SHELL_PROFILE"
            info "Added Homebrew to $SHELL_PROFILE"
        fi
    else
        error "Failed to install ARM64 Homebrew"
        exit 1
    fi
}

# Install Python 3.11 via Homebrew
install_python() {
    info "Checking Python installation..."

    # Check if Python 3.11 is already installed
    if [ -f "/opt/homebrew/bin/python3.11" ]; then
        PYTHON_VERSION=$(arch -arm64 /opt/homebrew/bin/python3.11 --version 2>&1 | cut -d' ' -f2)
        success "Python 3.11 already installed: $PYTHON_VERSION"
        PYTHON_PATH="/opt/homebrew/bin/python3.11"
        return 0
    fi

    info "Installing Python 3.11 via Homebrew..."

    # Install as actual user
    su - "$ACTUAL_USER" -c "arch -arm64 $BREW_PATH install python@3.11"

    if [ -f "/opt/homebrew/bin/python3.11" ]; then
        PYTHON_VERSION=$(arch -arm64 /opt/homebrew/bin/python3.11 --version 2>&1 | cut -d' ' -f2)
        success "Python 3.11 installed: $PYTHON_VERSION"
        PYTHON_PATH="/opt/homebrew/bin/python3.11"
    else
        error "Failed to install Python 3.11"
        exit 1
    fi
}

# Verify Python architecture
verify_python() {
    info "Verifying Python architecture..."

    # Check file architecture
    PYTHON_ARCH=$(file "$PYTHON_PATH" | grep -o "arm64" || echo "unknown")
    if [ "$PYTHON_ARCH" != "arm64" ]; then
        error "Python is not ARM64 architecture"
        file "$PYTHON_PATH"
        exit 1
    fi

    # Check runtime architecture
    RUNTIME_ARCH=$(arch -arm64 "$PYTHON_PATH" -c "import platform; print(platform.machine())" 2>&1)
    if [ "$RUNTIME_ARCH" != "arm64" ]; then
        error "Python runtime is not ARM64 (got: $RUNTIME_ARCH)"
        exit 1
    fi

    success "Python is native ARM64"
}

# Create virtual environment
create_venv() {
    info "Creating virtual environment..."

    PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
    VENV_PATH="$PROJECT_ROOT/packages/voice/.venv"

    # Remove old venv if exists
    if [ -d "$VENV_PATH" ]; then
        warning "Removing existing virtual environment"
        rm -rf "$VENV_PATH"
    fi

    # Create venv as actual user
    su - "$ACTUAL_USER" -c "cd '$PROJECT_ROOT/packages/voice' && arch -arm64 $PYTHON_PATH -m venv .venv"

    if [ -d "$VENV_PATH" ]; then
        success "Virtual environment created at packages/voice/.venv"

        # Verify venv Python is ARM64
        VENV_PYTHON="$VENV_PATH/bin/python"
        VENV_ARCH=$(arch -arm64 "$VENV_PYTHON" -c "import platform; print(platform.machine())" 2>&1)

        if [ "$VENV_ARCH" = "arm64" ]; then
            success "Virtual environment Python is ARM64"
        else
            error "Virtual environment Python is not ARM64 (got: $VENV_ARCH)"
            exit 1
        fi
    else
        error "Failed to create virtual environment"
        exit 1
    fi
}

# Install xswarm-voice package
install_package() {
    info "Installing xswarm-voice package..."

    PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
    VENV_PATH="$PROJECT_ROOT/packages/voice/.venv"
    VENV_PYTHON="$VENV_PATH/bin/python"
    VENV_PIP="$VENV_PATH/bin/pip"

    # Upgrade pip first
    su - "$ACTUAL_USER" -c "cd '$PROJECT_ROOT/packages/voice' && arch -arm64 '$VENV_PYTHON' -m pip install --upgrade pip"

    # Install package in development mode
    info "Installing dependencies (this may take a few minutes)..."
    su - "$ACTUAL_USER" -c "cd '$PROJECT_ROOT/packages/voice' && arch -arm64 '$VENV_PIP' install -e ."

    success "xswarm-voice package installed"
}

# Verify installation
verify_installation() {
    info "Verifying installation..."

    PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
    VENV_PYTHON="$PROJECT_ROOT/packages/voice/.venv/bin/python"

    # Check Python version and architecture
    PYTHON_INFO=$(arch -arm64 "$VENV_PYTHON" -c "import platform; print(f'{platform.python_version()} on {platform.machine()}')" 2>&1)
    success "Python: $PYTHON_INFO"

    # Check MLX
    if arch -arm64 "$VENV_PYTHON" -c "import mlx.core as mx; print(mx.__version__)" &>/dev/null; then
        MLX_VERSION=$(arch -arm64 "$VENV_PYTHON" -c "import mlx.core as mx; print(mx.__version__)" 2>&1)
        success "MLX: $MLX_VERSION"
    else
        error "MLX not installed or not working"
        exit 1
    fi

    # Check rustymimi
    if arch -arm64 "$VENV_PYTHON" -c "import rustymimi" &>/dev/null; then
        success "rustymimi: installed"
    else
        error "rustymimi not installed"
        exit 1
    fi

    # Check moshi_mlx
    if arch -arm64 "$VENV_PYTHON" -c "from moshi_mlx import models" &>/dev/null; then
        success "moshi_mlx: installed"
    else
        error "moshi_mlx not installed"
        exit 1
    fi
}

# Run test
run_test() {
    info "Testing MOSHI model loading..."

    PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
    VENV_PYTHON="$PROJECT_ROOT/packages/voice/.venv/bin/python"
    TEST_SCRIPT="$PROJECT_ROOT/packages/voice/test_moshi.py"

    if [ ! -f "$TEST_SCRIPT" ]; then
        warning "test_moshi.py not found, skipping test"
        return 0
    fi

    info "This will download ~4GB from Hugging Face on first run"
    info "Running test as $ACTUAL_USER..."

    # Run test as actual user
    su - "$ACTUAL_USER" -c "cd '$PROJECT_ROOT/packages/voice' && arch -arm64 '$VENV_PYTHON' test_moshi.py"

    if [ $? -eq 0 ]; then
        success "MOSHI test completed successfully"
    else
        warning "MOSHI test failed (this may be due to network issues)"
        warning "Try running manually: cd packages/voice && source .venv/bin/activate && python test_moshi.py"
    fi
}

# Print usage instructions
print_usage() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}║  ✓ MOSHI Python ARM64 Setup Complete!                   ║${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "To use MOSHI:"
    echo ""
    echo "  1. Activate virtual environment:"
    echo "     cd packages/voice"
    echo "     source .venv/bin/activate"
    echo ""
    echo "  2. Test MOSHI model:"
    echo "     python test_moshi.py"
    echo ""
    echo "  3. Use in your code:"
    echo "     from xswarm_voice import VoiceBridge"
    echo ""
    echo "Next steps:"
    echo "  - Implement Twilio Media Streams WebSocket server"
    echo "  - Test phone call with MOSHI voice"
    echo "  - Capture and implement voice feedback"
    echo ""
}

# Main execution
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║                                                          ║"
    echo "║       MOSHI Voice Model - ARM64 Python Setup             ║"
    echo "║                                                          ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""

    check_sudo
    check_architecture
    check_macos_version
    setup_homebrew
    install_python
    verify_python
    create_venv
    install_package
    verify_installation

    echo ""
    info "Setup complete! Testing MOSHI..."
    run_test

    print_usage
}

# Run main
main "$@"
