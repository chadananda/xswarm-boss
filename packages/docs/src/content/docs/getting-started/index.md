---
title: Installation
description: Install xSwarm-boss on your system
---

## System Requirements

- **OS**: Linux (Arch/Omarchy recommended, Ubuntu/Debian supported)
- **Architecture**: x86_64 or ARM64
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 2GB for installation
- **Optional**: GPU for local LLM inference

## Quick Install

### One-Line Install (Recommended)

```bash
curl -sSf https://xswarm.dev/install.sh | sh
```

This script will:
1. Detect your system architecture
2. Download the latest xSwarm binary
3. Install to `/usr/local/bin/xswarm`
4. Run the setup wizard

### Manual Install

#### Arch Linux (AUR)

```bash
yay -S xswarm-boss
# or
paru -S xswarm-boss
```

#### Debian/Ubuntu

```bash
wget https://github.com/chadananda/xswarm-boss/releases/latest/download/xswarm_amd64.deb
sudo dpkg -i xswarm_amd64.deb
```

#### AppImage (Universal)

```bash
wget https://github.com/chadananda/xswarm-boss/releases/latest/download/xswarm.AppImage
chmod +x xswarm.AppImage
sudo mv xswarm.AppImage /usr/local/bin/xswarm
```

#### Build from Source

```bash
git clone https://github.com/chadananda/xswarm-boss.git
cd xswarm-boss
cargo build --release
sudo cp target/release/xswarm /usr/local/bin/
```

## Setup Wizard

After installation, run the setup wizard:

```bash
xswarm setup
```

The wizard will guide you through:
1. **Theme Selection** - Choose your AI personality
2. **GPU Configuration** - Local or remote GPU setup
3. **Voice Setup** - Configure wake word and voice provider
4. **Vassal Discovery** - Find other machines on your network

## Verify Installation

```bash
xswarm --version
# xSwarm-boss 0.1.0

xswarm theme current
# hal-9000

xswarm config show
# Shows your configuration
```

## Next Steps

- [Quick Start](/getting-started/quick-start/) - Configure your first vassal
- [First Commands](/getting-started/first-commands/) - Learn basic usage
- [Choose a Theme](/themes/) - Pick your AI personality
