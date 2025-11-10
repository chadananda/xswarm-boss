"""
Comprehensive responsive testing for all TUI components.

Tests components at extreme sizes to ensure adaptive/responsive behavior:
- Tiny terminals (30x10)
- Very narrow (40x15)
- Standard (80x30)
- Large (120x40)
- Ultra-wide (200x30)
- Very tall (80x60)
- 4K terminal (200x60)

Run: pytest tests/test_responsive_comprehensive.py -v
Update baselines: pytest tests/test_responsive_comprehensive.py --snapshot-update
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.dashboard.widgets.panels.voice_visualizer_panel import (
    VoiceVisualizerPanel,
    VisualizationStyle,
    MicrophoneWaveformStyle,
)
from assistant.dashboard.widgets.panels.chat_panel import ChatPanel
from textual.app import App, ComposeResult


# Common terminal sizes to test
TERMINAL_SIZES = [
    ((30, 10), "tiny"),          # Minimum viable size
    ((40, 15), "very_small"),    # Very small terminal
    ((60, 20), "small"),         # Small terminal
    ((80, 24), "default_linux"), # Default Linux terminal
    ((80, 30), "standard"),      # Standard terminal
    ((100, 30), "medium"),       # Medium terminal
    ((120, 40), "large"),        # Large terminal
    ((160, 30), "ultra_wide"),   # Ultra-wide terminal
    ((80, 50), "very_tall"),     # Very tall terminal
    ((200, 60), "4k"),           # 4K terminal
]


class VoiceVisualizerApp(App):
    """App for voice visualizer testing."""

    def __init__(self, style: VisualizationStyle):
        super().__init__()
        self.style = style

    def compose(self) -> ComposeResult:
        panel = VoiceVisualizerPanel(
            visualization_style=self.style,
            microphone_waveform_style=MicrophoneWaveformStyle.SCROLLING_FILL,
        )
        panel.simulation_mode = True
        panel.amplitude = 0.6
        yield panel


class ChatPanelApp(App):
    """App for chat panel testing."""

    def __init__(self, messages=None):
        super().__init__()
        self.messages = messages or []

    def compose(self) -> ComposeResult:
        chat = ChatPanel()
        for role, content in self.messages:
            chat.add_message(role, content)
        yield chat


class TestVoiceVisualizerResponsive:
    """Test voice visualizer at all terminal sizes."""

    @pytest.mark.parametrize("size,size_name", TERMINAL_SIZES)
    def test_sound_wave_circle_all_sizes(self, snap_compare, size, size_name):
        """Test SOUND_WAVE_CIRCLE (selected style) at all terminal sizes."""

        async def run_before(pilot):
            await pilot.pause(0.5)

        app = VoiceVisualizerApp(VisualizationStyle.SOUND_WAVE_CIRCLE)
        assert snap_compare(app, terminal_size=size, run_before=run_before)

    @pytest.mark.parametrize("size,size_name", TERMINAL_SIZES)
    def test_concentric_circles_all_sizes(self, snap_compare, size, size_name):
        """Test CONCENTRIC_CIRCLES at all terminal sizes."""

        async def run_before(pilot):
            await pilot.pause(0.5)

        app = VoiceVisualizerApp(VisualizationStyle.CONCENTRIC_CIRCLES)
        assert snap_compare(app, terminal_size=size, run_before=run_before)

    # Test key sizes for all other styles (to keep test time reasonable)
    @pytest.mark.parametrize(
        "style,style_name",
        [
            (VisualizationStyle.RIPPLE_WAVES, "ripple_waves"),
            (VisualizationStyle.CIRCULAR_BARS, "circular_bars"),
            (VisualizationStyle.PULSING_DOTS, "pulsing_dots"),
            (VisualizationStyle.SPINNING_INDICATOR, "spinning_indicator"),
        ],
    )
    @pytest.mark.parametrize(
        "size,size_name",
        [
            ((30, 10), "tiny"),
            ((80, 30), "standard"),
            ((200, 60), "4k"),
        ],
    )
    def test_other_styles_key_sizes(self, snap_compare, style, style_name, size, size_name):
        """Test other visualization styles at key sizes (tiny, standard, 4k)."""

        async def run_before(pilot):
            await pilot.pause(0.5)

        app = VoiceVisualizerApp(style)
        assert snap_compare(app, terminal_size=size, run_before=run_before)


class TestChatPanelResponsive:
    """Test chat panel at all terminal sizes."""

    @pytest.mark.parametrize("size,size_name", TERMINAL_SIZES)
    def test_chat_empty_all_sizes(self, snap_compare, size, size_name):
        """Test empty chat panel at all terminal sizes."""
        assert snap_compare(ChatPanelApp(), terminal_size=size)

    @pytest.mark.parametrize("size,size_name", TERMINAL_SIZES)
    def test_chat_conversation_all_sizes(self, snap_compare, size, size_name):
        """Test chat panel with conversation at all terminal sizes."""
        messages = [
            ("user", "Hello!"),
            ("assistant", "Hi there! How can I help you?"),
            ("user", "Just testing the UI at different sizes."),
            ("assistant", "Looks great! The chat panel adapts to any terminal size."),
        ]
        assert snap_compare(ChatPanelApp(messages), terminal_size=size)

    @pytest.mark.parametrize("size,size_name", TERMINAL_SIZES)
    def test_chat_long_message_all_sizes(self, snap_compare, size, size_name):
        """Test chat panel with long message (word wrapping) at all sizes."""
        messages = [
            ("user", "Can you explain what quantum computing is and how it differs from classical computing in a detailed way?"),
            ("assistant", "Quantum computing is a type of computation that harnesses quantum mechanical phenomena like superposition and entanglement. Unlike classical computers that use bits (0 or 1), quantum computers use qubits that can exist in multiple states simultaneously."),
        ]
        assert snap_compare(ChatPanelApp(messages), terminal_size=size)


class TestExtremeSizes:
    """Test edge cases and extreme terminal sizes."""

    def test_voice_visualizer_minimum_viable(self, snap_compare):
        """Test voice visualizer at absolute minimum size (30x10)."""

        async def run_before(pilot):
            await pilot.pause(0.5)

        app = VoiceVisualizerApp(VisualizationStyle.SOUND_WAVE_CIRCLE)
        assert snap_compare(app, terminal_size=(30, 10), run_before=run_before)

    def test_chat_panel_minimum_viable(self, snap_compare):
        """Test chat panel at absolute minimum size (30x10)."""
        messages = [("user", "Hi"), ("assistant", "Hello!")]
        assert snap_compare(ChatPanelApp(messages), terminal_size=(30, 10))

    def test_voice_visualizer_ultra_wide(self, snap_compare):
        """Test voice visualizer in ultra-wide terminal (200x30)."""

        async def run_before(pilot):
            await pilot.pause(0.5)

        app = VoiceVisualizerApp(VisualizationStyle.SOUND_WAVE_CIRCLE)
        assert snap_compare(app, terminal_size=(200, 30), run_before=run_before)

    def test_chat_panel_ultra_wide(self, snap_compare):
        """Test chat panel in ultra-wide terminal (200x30)."""
        messages = [
            ("user", "Testing ultra-wide terminal"),
            ("assistant", "The chat panel should adapt gracefully to ultra-wide terminals with proper layout."),
        ]
        assert snap_compare(ChatPanelApp(messages), terminal_size=(200, 30))

    def test_voice_visualizer_very_tall(self, snap_compare):
        """Test voice visualizer in very tall terminal (80x60)."""

        async def run_before(pilot):
            await pilot.pause(0.5)

        app = VoiceVisualizerApp(VisualizationStyle.SOUND_WAVE_CIRCLE)
        assert snap_compare(app, terminal_size=(80, 60), run_before=run_before)

    def test_chat_panel_very_tall(self, snap_compare):
        """Test chat panel in very tall terminal (80x60) with many messages."""
        messages = [(("user" if i % 2 == 0 else "assistant"), f"Message {i}") for i in range(30)]
        assert snap_compare(ChatPanelApp(messages), terminal_size=(80, 60))

    def test_voice_visualizer_4k_terminal(self, snap_compare):
        """Test voice visualizer in 4K terminal (200x60)."""

        async def run_before(pilot):
            await pilot.pause(0.5)

        app = VoiceVisualizerApp(VisualizationStyle.SOUND_WAVE_CIRCLE)
        assert snap_compare(app, terminal_size=(200, 60), run_before=run_before)

    def test_chat_panel_4k_terminal(self, snap_compare):
        """Test chat panel in 4K terminal (200x60) with conversation."""
        messages = [
            ("user", "What's the meaning of life?"),
            ("assistant", "The meaning of life is a philosophical question that has been debated for centuries. Different people and cultures have different perspectives."),
            ("user", "Can you elaborate?"),
            ("assistant", "Certainly! Some find meaning in relationships, others in personal achievement, creativity, helping others, or spiritual pursuits. It's deeply personal."),
        ]
        assert snap_compare(ChatPanelApp(messages), terminal_size=(200, 60))


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--snapshot-update"])
