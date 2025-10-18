#!/bin/bash
# Download the BEST animated icons for all xSwarm personas
# Based on comprehensive research by 5 parallel subagents
# See docs/ICON_SELECTION_GUIDE.md for full research details

set -e

echo "🎨 xSwarm Persona Icon Downloader (BEST QUALITY)"
echo "=================================================="
echo ""
echo "Downloading highest quality animated icons based on extensive research..."
echo ""

PERSONAS_DIR="packages/personas"

# Check dependencies
if ! command -v curl &> /dev/null; then
    echo "❌ Error: curl is not installed"
    exit 1
fi

# HAL 9000 - LottieFiles (will need manual download for best quality)
echo "📥 HAL 9000..."
echo "   ⚠️  Best option requires manual download:"
echo "   Visit: https://lottiefiles.com/free-animation/hal-9000-q9fQTicaTj"
echo "   Download as GIF (512x512 or 1024x1024)"
echo "   Save to: packages/personas/hal-9000/icon.gif"
echo ""
echo "   Alternative (auto-download, good quality):"
curl -sL "https://media.giphy.com/media/l0HlNyrvLKBMxjFzG/giphy.gif" \
  -o "$PERSONAS_DIR/hal-9000/icon.gif" && echo "   ✅ Downloaded fallback option" || echo "   ❌ Failed"
echo ""

# KITT - Tenor
echo "📥 KITT..."
echo "   Manual download recommended for best quality:"
echo "   Visit: https://tenor.com/view/knightrider-kitt-tv-car-scanner-gif-11191600"
echo "   Right-click and 'Save Image As...' to packages/personas/kitt/icon.gif"
echo ""

# GLaDOS - Tenor 498x498 (highest quality found)
echo "📥 GLaDOS..."
echo "   Manual download recommended (19.2MB highest quality):"
echo "   Visit: https://tenor.com/view/glados-gif-26217945"
echo "   Right-click and save to packages/personas/glados/icon.gif"
echo ""
echo "   Alternative (auto-download, good quality):"
curl -sL "https://media.giphy.com/media/8vtm3YCdxtUvjTn0U3/giphy.gif" \
  -o "$PERSONAS_DIR/glados/icon.gif" && echo "   ✅ Downloaded fallback" || echo "   ❌ Failed"
echo ""

# Cylon - GIPHY Official PeacockTV
echo "📥 Cylon..."
curl -sL "https://media.giphy.com/media/kBlljXO6nyVLCfrJ5E/giphy.gif" \
  -o "$PERSONAS_DIR/cylon/icon.gif" && echo "   ✅ Downloaded (Official PeacockTV source)" || echo "   ❌ Failed"
echo ""

# C-3PO - GIPHY Official Star Wars
echo "📥 C-3PO..."
curl -sL "https://media.giphy.com/media/3ohuPqvqWs2pFkeure/giphy.gif" \
  -o "$PERSONAS_DIR/c3po/icon.gif" && echo "   ✅ Downloaded (Official Star Wars)" || echo "   ❌ Failed"
echo ""

# TARS - Tenor (manual recommended for 12.9MB version)
echo "📥 TARS..."
echo "   Manual download recommended for best quality (12.9MB):"
echo "   Visit: https://tenor.com/view/interstellar-tars-ocean-running-transform-gif-9424140225652247665"
echo "   Right-click and save to packages/personas/tars/icon.gif"
echo ""

# Marvin - Tenor
echo "📥 Marvin..."
echo "   Manual download recommended:"
echo "   Visit: https://tenor.com/view/the-hitchhikers-guide-to-the-galaxy-marvin-the-paranoid-android-its-even-worse-that-i-thought-it-would-be-worse-that-i-thought-got-worse-gif-21730765"
echo "   Right-click and save to packages/personas/marvin/icon.gif"
echo ""
echo "   Alternative (auto-download):"
curl -sL "https://media.giphy.com/media/l0HlN5Y28D9MzzcRy/giphy.gif" \
  -o "$PERSONAS_DIR/marvin/icon.gif" && echo "   ✅ Downloaded fallback" || echo "   ❌ Failed"
echo ""

# Sauron - Tenor (2.8MB highest quality)
echo "📥 Sauron..."
echo "   Manual download recommended (2.8MB highest quality):"
echo "   Visit: https://tenor.com/view/sauron-eye-tower-lord-of-the-rings-i-see-you-gif-25761843"
echo "   Right-click and save to packages/personas/sauron/icon.gif"
echo ""
echo "   Alternative (auto-download):"
curl -sL "https://media.giphy.com/media/njYrp176NQsHS/giphy.gif" \
  -o "$PERSONAS_DIR/sauron/icon.gif" && echo "   ✅ Downloaded fallback" || echo "   ❌ Failed"
echo ""

# JARVIS - LottieFiles (manual only)
echo "📥 JARVIS..."
echo "   Manual download required:"
echo "   Visit: https://lottiefiles.com/free-animation/voice-assistant-ai-chatbot-TU0uS5jXMP"
echo "   Download as GIF, save to packages/personas/jarvis/icon.gif"
echo ""

# DALEK - GIPHY Official BBC
echo "📥 DALEK..."
curl -sL "https://media.giphy.com/media/XPyyhPIi05Z0C8xgpb/giphy.gif" \
  -o "$PERSONAS_DIR/dalek/icon.gif" && echo "   ✅ Downloaded (Official BBC Doctor Who)" || echo "   ❌ Failed"
echo ""

echo "=================================================="
echo "✅ Auto-downloads completed: Cylon, C-3PO, DALEK"
echo "⚠️  Manual downloads recommended for best quality:"
echo "   - HAL 9000 (4K from LottieFiles)"
echo "   - KITT (Archive.org cinemagraph)"
echo "   - GLaDOS (19.2MB Tenor)"
echo "   - TARS (12.9MB Tenor)"
echo "   - Marvin (1.8MB Tenor)"
echo "   - Sauron (2.8MB Tenor)"
echo "   - JARVIS (LottieFiles voice waveform)"
echo ""
echo "📖 See docs/ICON_SELECTION_GUIDE.md for detailed instructions"
echo ""
echo "🎉 Done! Check packages/personas/*/icon.gif"
