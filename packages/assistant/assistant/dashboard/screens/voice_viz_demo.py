"""
Voice Visualizer Demo Screen

Shows all 6 visualization styles side-by-side for comparison.
User can see them in action and decide which to keep.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Grid, Vertical
from textual.widgets import Header, Footer, Static, Label
from textual.reactive import reactive

from ..widgets.panels import VoiceVisualizerPanel, VisualizationStyle


class VoiceVizDemoScreen(Screen):
    """
    Demo screen showing all 6 voice visualization styles.

    Layout: 3x2 grid of visualization panels.
    Each panel shows a different style with a label.
    """

    CSS = """
    VoiceVizDemoScreen {
        background: #0a0e27;
    }

    #demo-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    #viz-grid {
        grid-size: 3 2;
        grid-gutter: 1;
        width: 100%;
        height: 100%;
    }

    .viz-container {
        border: solid #00d4ff;
        height: 100%;
        width: 100%;
    }

    .viz-label {
        background: #1a1f3a;
        color: #00d4ff;
        text-align: center;
        height: 1;
        text-style: bold;
    }

    VoiceVisualizerPanel {
        height: 1fr;
        border: none;
    }
    """

    BINDINGS = [
        ("escape", "dismiss", "Back"),
        ("q", "dismiss", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the demo screen layout."""
        yield Header()

        with Container(id="demo-container"):
            with Grid(id="viz-grid"):
                # Style 1: Concentric Circles
                with Vertical(classes="viz-container"):
                    yield Label("1. Concentric Circles", classes="viz-label")
                    panel1 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.CONCENTRIC_CIRCLES
                    )
                    panel1.simulation_mode = True
                    panel1.start_animation()
                    yield panel1

                # Style 2: Ripple Waves
                with Vertical(classes="viz-container"):
                    yield Label("2. Ripple Waves", classes="viz-label")
                    panel2 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.RIPPLE_WAVES
                    )
                    panel2.simulation_mode = True
                    panel2.start_animation()
                    yield panel2

                # Style 3: Circular Bars
                with Vertical(classes="viz-container"):
                    yield Label("3. Circular Bars", classes="viz-label")
                    panel3 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.CIRCULAR_BARS
                    )
                    panel3.simulation_mode = True
                    panel3.start_animation()
                    yield panel3

                # Style 4: Pulsing Dots
                with Vertical(classes="viz-container"):
                    yield Label("4. Pulsing Dots", classes="viz-label")
                    panel4 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.PULSING_DOTS
                    )
                    panel4.simulation_mode = True
                    panel4.start_animation()
                    yield panel4

                # Style 5: Spinning Indicator
                with Vertical(classes="viz-container"):
                    yield Label("5. Spinning Indicator", classes="viz-label")
                    panel5 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SPINNING_INDICATOR
                    )
                    panel5.simulation_mode = True
                    panel5.start_animation()
                    yield panel5

                # Style 6: Sound Wave Circle
                with Vertical(classes="viz-container"):
                    yield Label("6. Sound Wave Circle", classes="viz-label")
                    panel6 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE
                    )
                    panel6.simulation_mode = True
                    panel6.start_animation()
                    yield panel6

        yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        # All panels start animating automatically in compose()
        pass

    def action_dismiss(self) -> None:
        """Dismiss the demo screen."""
        # Stop all animations before dismissing
        panels = self.query(VoiceVisualizerPanel)
        for panel in panels:
            panel.stop_animation()

        self.dismiss()
