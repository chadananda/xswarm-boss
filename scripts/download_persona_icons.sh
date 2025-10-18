#!/bin/bash
# Download best animated icons for all xSwarm personas
#
# This script downloads the highest quality animated GIFs for each persona
# and saves them as icon.gif in each persona's folder.
#
# Usage:
#   chmod +x scripts/download_persona_icons.sh
#   ./scripts/download_persona_icons.sh

set -e

echo "🎨 xSwarm Persona Icon Downloader"
echo "=================================="
echo ""

# Persona icon URLs (best quality animated GIFs)
declare -A ICONS=(
  ["hal-9000"]="https://media.giphy.com/media/l0HlNyrvLKBMxjFzG/giphy.gif"
  ["kitt"]="https://media.tenor.com/QVPOKZDrWb4AAAAC/knight-rider-scanner.gif"
  ["glados"]="https://media.giphy.com/media/8vtm3YCdxtUvjTn0U3/giphy.gif"
  ["cylon"]="https://media.giphy.com/media/xT9DPCKNlqT6RznP9K/giphy.gif"
  ["c3po"]="https://media.giphy.com/media/3o7TKS6AWINqbg3FV6/giphy.gif"
  ["tars"]="https://media.giphy.com/media/3o7aCTPPm4OHfRLSH6/giphy.gif"
  ["marvin"]="https://media.giphy.com/media/l0HlN5Y28D9MzzcRy/giphy.gif"
  ["sauron"]="https://media.giphy.com/media/njYrp176NQsHS/giphy.gif"
  ["dalek"]="https://media.giphy.com/media/3o6ZtjWdtTFfpCMEj6/giphy.gif"
  ["jarvis"]="https://64.media.tumblr.com/d6a5e895f8c40e4cb8fa3b44c6ede0fe/tumblr_ocefbddRxg1up7w8xo1_540.gifv"
)

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    echo "❌ Error: curl is not installed"
    echo "   Install with: brew install curl (macOS) or sudo apt install curl (Linux)"
    exit 1
fi

# Base path for personas
PERSONAS_DIR="packages/personas"

if [ ! -d "$PERSONAS_DIR" ]; then
    echo "❌ Error: $PERSONAS_DIR directory not found"
    echo "   Run this script from the project root directory"
    exit 1
fi

# Download icons
successful=0
failed=0
total=${#ICONS[@]}

for persona in "${!ICONS[@]}"; do
    url="${ICONS[$persona]}"
    output="$PERSONAS_DIR/$persona/icon.gif"

    if [ ! -d "$PERSONAS_DIR/$persona" ]; then
        echo "⚠️  Skipping $persona (directory not found)"
        ((failed++))
        continue
    fi

    echo -n "Downloading $persona icon... "

    if curl -sL "$url" -o "$output" 2>/dev/null; then
        if [ -f "$output" ] && [ -s "$output" ]; then
            size=$(du -h "$output" | cut -f1)
            echo "✅ ($size)"
            ((successful++))
        else
            echo "❌ (download failed or empty)"
            rm -f "$output"
            ((failed++))
        fi
    else
        echo "❌ (curl error)"
        ((failed++))
    fi
done

echo ""
echo "=================================="
echo "📊 Download Summary:"
echo "   ✅ Successful: $successful/$total"
echo "   ❌ Failed: $failed/$total"
echo ""

if [ $successful -gt 0 ]; then
    echo "🎉 Icons saved to packages/personas/*/icon.gif"
    echo ""
    echo "📝 Optional next steps:"
    echo "   1. Convert to APNG: ffmpeg -i icon.gif icon.apng"
    echo "   2. Optimize size: gifsicle -O3 icon.gif -o icon_optimized.gif"
    echo "   3. Commit icons: git add packages/personas/*/icon.gif"
    echo ""
    echo "⚠️  Note: JARVIS icon may need manual review (no official animated icon exists)"
fi

exit 0
