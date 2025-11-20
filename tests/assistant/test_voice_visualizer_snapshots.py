"""
Snapshot tests for Voice Visualizer Panel.

These tests use pytest-textual-snapshot to capture visual snapshots of the
voice visualizer at different states and terminal sizes. Tests run in headless
mode (no terminal corruption).

Run tests: pytest tests/test_voice_visualizer_snapshots.py
Update baselines: pytest tests/test_voice_visualizer_snapshots.py --snapshot-update
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.dashboard.widgets.panels.voice_visualizer_panel import (
    VoiceVisualizerPanel,
    VisualizationStyle,
    MicrophoneWaveformStyle,
)
from textual.app import App, ComposeResult


class TestVisualizerApp(App):
    """Test app that displays a single VoiceVisualizerPanel."""

    def __init__(self, style: VisualizationStyle, mic_style: MicrophoneWaveformStyle = MicrophoneWaveformStyle.SCROLLING_FILL):
        super().__init__()
        self.style = style
        self.mic_style = mic_style

    def compose(self) -> ComposeResult:
        panel = VoiceVisualizerPanel(
            visualization_style=self.style,
            microphone_waveform_style=self.mic_style,
        )
        panel.simulation_mode = True
        panel.amplitude = 0.5  # Set to mid-level amplitude for consistent snapshots
        yield panel


class TestVoiceVisualizerSnapshots:
    """Test voice visualizer visual output with snapshots."""

    @pytest.mark.parametrize(
        "style,name",
        [
            (VisualizationStyle.CONCENTRIC_CIRCLES, "concentric_circles"),
            (VisualizationStyle.RIPPLE_WAVES, "ripple_waves"),
            (VisualizationStyle.CIRCULAR_BARS, "circular_bars"),
            (VisualizationStyle.PULSING_DOTS, "pulsing_dots"),
            (VisualizationStyle.SPINNING_INDICATOR, "spinning_indicator"),
            (VisualizationStyle.SOUND_WAVE_CIRCLE, "sound_wave_circle"),
        ],
    )
    def test_visualizer_style_standard_size(self, snap_compare, style, name):
        """Test each visualization style at standard 80x30 terminal size."""

        async def run_before(pilot):
            # Let animation run to stable frame
            await pilot.pause(0.5)

        assert snap_compare(
            TestVisualizerApp(style), terminal_size=(80, 30), run_before=run_before
        )

    @pytest.mark.parametrize(
        "style",
        [
            VisualizationStyle.SOUND_WAVE_CIRCLE,  # Test the selected style
        ],
    )
    @pytest.mark.parametrize(
        "size,size_name",
        [
            ((40, 15), "small"),
            ((80, 30), "standard"),
            ((120, 40), "large"),
        ],
    )
    def test_visualizer_responsive_sizes(self, snap_compare, style, size, size_name):
        """Test selected visualization style at multiple terminal sizes."""

        async def run_before(pilot):
            await pilot.pause(0.5)

        assert snap_compare(
            TestVisualizerApp(style), terminal_size=size, run_before=run_before
        )

    def test_visualizer_idle_state(self, snap_compare):
        """Test visualizer in idle state (low amplitude)."""

        async def run_before(pilot):
            app = pilot.app
            # Set idle state
            panel = app.query_one(VoiceVisualizerPanel)
            panel.amplitude = 0.0
            await pilot.pause(0.3)

        app = TestVisualizerApp(VisualizationStyle.SOUND_WAVE_CIRCLE)
        assert snap_compare(app, terminal_size=(80, 30), run_before=run_before)

    def test_visualizer_active_state(self, snap_compare):
        """Test visualizer in active/speaking state (high amplitude)."""

        async def run_before(pilot):
            app = pilot.app
            # Set active state
            panel = app.query_one(VoiceVisualizerPanel)
            panel.amplitude = 0.9
            await pilot.pause(0.3)

        app = TestVisualizerApp(VisualizationStyle.SOUND_WAVE_CIRCLE)
        assert snap_compare(app, terminal_size=(80, 30), run_before=run_before)

    @pytest.mark.parametrize(
        "mic_style,name",
        [
            (MicrophoneWaveformStyle.SCROLLING_FILL, "scrolling_fill"),
            (MicrophoneWaveformStyle.VERTICAL_BARS, "vertical_bars"),
            (MicrophoneWaveformStyle.WAVE_CHARACTERS, "wave_characters"),
            (MicrophoneWaveformStyle.LINE_WAVE, "line_wave"),
            (MicrophoneWaveformStyle.DOTS, "dots"),
        ],
    )
    def test_microphone_waveform_styles(self, snap_compare, mic_style, name):
        """Test different microphone waveform styles."""

        async def run_before(pilot):
            await pilot.pause(0.5)

        app = TestVisualizerApp(
            VisualizationStyle.SOUND_WAVE_CIRCLE, mic_style=mic_style
        )
        assert snap_compare(app, terminal_size=(80, 30), run_before=run_before)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--snapshot-update"])
