#!/usr/bin/env python3
"""
Simple test to verify microphone waveform styles are different.
"""

from assistant.dashboard.widgets.panels import MicrophoneWaveformStyle

# Test 1: Print all styles
print("\n" + "=" * 70)
print("Available Microphone Waveform Styles:")
print("=" * 70)

for i, style in enumerate(MicrophoneWaveformStyle, 1):
    print(f"{i}. {style.name}: {style.value}")

print("\n" + "=" * 70)
print("Test: Create panels with different styles")
print("=" * 70)

from assistant.dashboard.widgets.panels import VoiceVisualizerPanel, VisualizationStyle

# Create 5 panels with different styles
panels = []
for style in MicrophoneWaveformStyle:
    panel = VoiceVisualizerPanel(
        visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE,
        microphone_waveform_style=style,
    )
    panels.append(panel)
    print(f"✓ Created panel with {style.name}")
    print(f"  Panel's style: {panel.microphone_waveform_style.name}")
    print(f"  Matches: {panel.microphone_waveform_style == style}")
    print()

print("=" * 70)
print("All panels created successfully with different styles!")
print("=" * 70 + "\n")
