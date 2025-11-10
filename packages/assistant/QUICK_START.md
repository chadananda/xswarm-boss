# Voice Assistant Dashboard - Quick Start

> **Note**: This is a developer guide for testing the dashboard visualizer component.
> For the full interactive TUI with configuration wizard and settings, see [README.md](README.md).

## Test the Pulsing Circle Visualizer NOW! 🎉

### One-Line Install & Run

```bash
cd /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/assistant && pip install textual rich torch && python examples/test_dashboard.py
```

### What You'll See

When you run the test script, you'll see a beautiful TUI dashboard with:

**Left Panel (60% width):**
- **Pulsing Circle Visualizer** (top 70%)
  - Cyan circle slowly breathing (idle state)
  - Changes color and animation based on state

- **Status Widget** (bottom 30%)
  - Device: cpu (or mps/cuda if available)
  - State: idle/listening/speaking/thinking
  - Keyboard controls

**Right Panel (40% width):**
- **Activity Feed**
  - Timestamped event log
  - Shows what's happening

### Interactive Controls

**Press SPACE** to cycle through states:
1. **Idle → Ready** (Blue, steady)
2. **Ready → Listening** (Green, fast pulse)
3. **Listening → Speaking** (Yellow, amplitude-driven pulse) ⭐
4. **Speaking → Thinking** (Magenta, rotating)
5. **Thinking → Ready** (Blue, steady)

**Press Q** to quit

### What Makes It Cool

**Speaking State** (the star of the show):
- Circle pulses with simulated speech amplitude
- Combines sine wave with random noise for realism
- Smooth transitions (10-frame averaging)
- Feels alive and natural!

### Expected Visual

```
┌─ Voice Assistant ────────────────────────────────────────┐
│                                                           │
│ ┌─ Visualizer ─────────┐  ┌─ Activity Log ─────────────┐ │
│ │                      │  │                             │ │
│ │                      │  │ [12:34:56] Test mode active │ │
│ │       ●●●●●          │  │ [12:34:57] Ready            │ │
│ │      ●●●●●●●         │  │ [12:35:01] Listening...     │ │
│ │     ●●●●●●●●●        │  │ [12:35:03] Speaking         │ │
│ │      ●●●●●●●         │  │ [12:35:05] Thinking         │ │
│ │       ●●●●●          │  │                             │ │
│ │                      │  │                             │ │
│ │                      │  │                             │ │
│ └──────────────────────┘  └─────────────────────────────┘ │
│ ┌─ Status ─────────────┐                                  │
│ │ Device: cpu          │                                  │
│ │ State: speaking      │  (changes color!)                │
│ │ Server: disconnected │                                  │
│ │                      │                                  │
│ │ Controls:            │                                  │
│ │   SPACE - Toggle     │                                  │
│ │   Q     - Quit       │                                  │
│ └──────────────────────┘                                  │
└───────────────────────────────────────────────────────────┘
```

### Terminal Recommendations

**Best experience:**
- iTerm2 (macOS)
- Windows Terminal (Windows 10+)
- GNOME Terminal (Linux)
- VSCode integrated terminal

**Window size:**
- Minimum: 80x24
- Recommended: 120x40 or larger
- Fullscreen for best experience

### Troubleshooting

**"Module not found: textual"**
```bash
pip install textual rich torch
```

**"Window too small"**
- Resize your terminal to at least 80x24 characters
- Or run in fullscreen

**Circle looks weird**
- Make sure your terminal supports Unicode (●, ○, ·)
- Try iTerm2 or Windows Terminal for best results

**Not animating**
- The visualizer updates at 30 FPS automatically
- Press SPACE to cycle states and see different animations

### What's Next?

This dashboard is ready for Phase 2 (MOSHI integration):
1. Connect real audio input
2. Replace simulated amplitude with MOSHI output
3. Add voice recognition
4. Become a real voice assistant!

### File Locations

- Test script: `examples/test_dashboard.py`
- Main app: `assistant/dashboard/app.py`
- Visualizer: `assistant/dashboard/widgets/visualizer.py` ⭐
- Documentation: `docs/phase3-dashboard-implementation.md`

---

**Ready to see your beautiful pulsing circle?**

Run this now:
```bash
python examples/test_dashboard.py
```

🎉 Enjoy the show!
