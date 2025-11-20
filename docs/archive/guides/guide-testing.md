# Moshi Voice Assistant - Testing Guide

## 🎯 What's Ready to Test

All backend features are implemented and committed:

✅ **Tool Calling** - Theme changes via voice  
✅ **Memory System** - Conversation history  
✅ **Persona Consistency** - Moshi identifies as current theme  
✅ **Auto Re-introductions** - After theme changes  
✅ **MLX Bridge** - Apple Silicon optimized  

---

## 🚀 Quick Start

```bash
cd packages/assistant
python -m assistant.dashboard.app
```

The app will:
1. Load MLX models (~1-2 minutes first time)
2. Show "Loading MOSHI MLX models..."  
3. Display visualizer when ready

---

## 🎤 Testing Voice Interaction

### Test 1: Basic Greeting
**Expected:** Moshi automatically greets you as JARVIS on startup

**What to check:**
- Top visualizer (circle) pulses with Moshi voice
- Greeting appears in chat history
- Audio plays through speakers

### Test 2: Mic Input
**Action:** Press SPACE, say something, press SPACE again

**What to check:**
- Bottom waveform shows dots sized by mic amplitude
- Dots appear on left, scroll right
- Pattern reflects your speech intensity

### Test 3: Voice Conversation
**Action:** Press SPACE → "Hello Jarvis, how are you?" → SPACE

**What to check:**
- User message appears in chat
- Moshi responds in JARVIS personality
- Response plays with visualizer animation
- Both messages stored in history

### Test 4: Theme Change via Voice
**Action:** Say "Change the theme to GLaDOS"

**Expected Flow:**
1. Moshi recognizes tool call
2. Activity feed shows: "🔧 Executing tool: change_theme"
3. Theme colors change to orange (#FFA500)
4. Visualizer border updates to "xSwarm - GLaDOS"
5. Moshi re-introduces: "Well well well..."

**What to check:**
- Orange theme applied
- GLaDOS personality in responses
- Automatic re-introduction happens
- No errors in activity feed

### Test 5: Persona Consistency
**After** changing to GLaDOS, say:
- "Tell me about science"
- "How are you doing?"

**Expected:**
- Sarcastic, Portal-like responses
- References to testing, cake, Aperture Science
- Maintains personality across conversation

### Test 6: Memory/Context
**Action:** Have a multi-turn conversation

```
You: "My favorite color is blue"
JARVIS: "I'll remember that..."
[... few more exchanges ...]
You: "What's my favorite color?"
JARVIS: "You mentioned it's blue"
```

**What to check:**
- Moshi references earlier parts of conversation
- Context maintained across multiple exchanges

---

## 🐛 What to Report

### If It Works:
- ✅ Which tests passed
- ✅ Any surprising behaviors (good or bad)
- ✅ Performance (response time, smoothness)

### If Something Breaks:
- ❌ Which test failed
- ❌ Error messages from activity feed
- ❌ What you expected vs what happened
- ❌ Screenshot if relevant

---

## 🎨 Visual Elements to Check

### Top Visualizer (Moshi Speaking):
- Pulsing circle animation
- Size changes with amplitude
- Smooth at 30 FPS
- Color matches theme

### Bottom Waveform (Mic Input):
- Dots sized by mic amplitude
- New dots appear left
- Scroll right
- Creates pattern of speech

### Activity Feed:
- Shows initialization progress
- Tool executions
- Error messages (if any)

### Chat History:
- User messages
- Moshi responses
- System messages (tool executions)
- Scrolls automatically

---

## ⚡ Known Limitations

1. **First Load Slow** - MLX models download/load (~1-2 min first time)
2. **MPS Not Supported** - Must use MLX on M3 (PyTorch MPS has 4GB limit)
3. **Mic Permission** - macOS will ask for microphone access

---

## 📋 Test Checklist

Copy this to track your testing:

```
## Basic Functionality
- [ ] App launches without errors
- [ ] Models load successfully
- [ ] Auto-greeting plays

## Voice Interaction
- [ ] Mic input captured
- [ ] Mic waveform visualizes
- [ ] Voice-to-voice conversation works
- [ ] Responses sound natural

## Tool Calling
- [ ] Theme change via voice works
- [ ] Auto re-introduction happens
- [ ] Tool execution shown in activity feed
- [ ] No errors during tool calls

## Persona System
- [ ] JARVIS personality consistent
- [ ] GLaDOS personality consistent
- [ ] Theme colors apply correctly
- [ ] Visualizer updates with theme

## Memory & Context
- [ ] Messages stored
- [ ] History retrieved in responses
- [ ] Context maintained across conversation

## Stability
- [ ] No crashes after 20+ messages
- [ ] Multiple theme changes work
- [ ] Animations stay smooth
- [ ] No memory leaks
```

---

## 🔧 Troubleshooting

### "MLX import error"
```bash
cd /tmp/moshi-official/moshi_mlx && pip install -e .
```

### "Models not found"
Models auto-download to `~/.cache/huggingface/hub/`  
Check: `ls -lh ~/.cache/huggingface/hub/ | grep moshiko-mlx`

### "No audio output"
- Check system sound settings
- Verify sounddevice package installed
- Test: `python -m sounddevice`

### "Mic not working"
- Grant microphone permission in System Settings
- Check microphone in other apps first

---

**Ready to test!** Run the app and try the scenarios above. Report back what works and what doesn't!
