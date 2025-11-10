"""
Base class for all TUI panels.

Provides consistent styling, state management, and voice command integration.
"""

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from abc import abstractmethod
from typing import Dict, Any, Optional


class PanelBase(Static):
    """
    Base class for all TUI panels (Chat, Documents, Todo, Projects, etc.).

    Features:
    - Common border and title styling
    - Focus state management
    - Minimize/maximize support
    - Notification badges
    - Voice command handling
    - Responsive sizing
    """

    # Reactive properties
    is_focused = reactive(False)
    is_minimized = reactive(False)
    notification_count = reactive(0)

    def __init__(
        self,
        panel_id: str,
        title: str,
        min_width: int = 30,
        min_height: int = 10,
        **kwargs
    ):
        """
        Initialize panel.

        Args:
            panel_id: Unique panel identifier
            title: Panel display title
            min_width: Minimum panel width
            min_height: Minimum panel height
        """
        super().__init__(**kwargs)
        self.panel_id = panel_id
        self.panel_title = title
        self.min_width = min_width
        self.min_height = min_height

    @abstractmethod
    def render_content(self) -> Text:
        """
        Render panel-specific content.

        Must be implemented by subclasses.

        Returns:
            Rich Text object with panel content
        """
        pass

    def render(self) -> Text:
        """
        Render complete panel with border, title, and content.

        Returns:
            Rich Text object with full panel rendering
        """
        result = Text()

        # Get dimensions
        widget_width = max(self.size.width, self.min_width)
        widget_height = max(self.size.height, self.min_height)

        # Border style based on focus state
        border_style = "bold cyan" if self.is_focused else "dim cyan"
        title_style = f"bold {'yellow' if self.is_focused else 'white'}"

        # Top border with title
        title_text = f" {self.panel_title} "

        # Add notification badge if present
        if self.notification_count > 0:
            title_text += f"({self.notification_count}) "

        title_len = len(title_text)
        remaining_width = widget_width - title_len - 2  # -2 for border chars

        result.append("╔", style=border_style)
        result.append(title_text, style=title_style)
        result.append("═" * max(0, remaining_width), style=border_style)
        result.append("╗\n", style=border_style)

        # Content (if not minimized)
        if not self.is_minimized:
            content = self.render_content()
            content_lines = content.split("\n") if content else []

            # Calculate available content height
            available_height = widget_height - 2  # -2 for borders

            # Render content lines
            for i, line in enumerate(content_lines):
                if i >= available_height:
                    break

                result.append("║ ", style=border_style)

                # Truncate line if too long
                line_str = str(line)
                max_line_width = widget_width - 4  # -4 for "║ " and " ║"
                if len(line_str) > max_line_width:
                    line_str = line_str[:max_line_width-3] + "..."

                result.append(line_str)

                # Pad to width
                padding = max(0, max_line_width - len(line_str))
                result.append(" " * padding)
                result.append(" ║\n", style=border_style)

            # Fill remaining vertical space
            remaining_lines = available_height - len(content_lines)
            for _ in range(max(0, remaining_lines)):
                result.append("║", style=border_style)
                result.append(" " * (widget_width - 2))
                result.append("║\n", style=border_style)

        # Bottom border
        result.append("╚" + "═" * (widget_width - 2) + "╝", style=border_style)

        return result

    # State management methods

    def focus_panel(self):
        """Focus this panel (highlight border)"""
        self.is_focused = True

    def blur_panel(self):
        """Unfocus this panel (dim border)"""
        self.is_focused = False

    def toggle_minimize(self):
        """Toggle panel minimized state"""
        self.is_minimized = not self.is_minimized

    def set_notification_count(self, count: int):
        """
        Set notification badge count.

        Args:
            count: Number of notifications (0 to hide badge)
        """
        self.notification_count = count

    def increment_notification(self):
        """Increment notification count"""
        self.notification_count += 1

    def clear_notifications(self):
        """Clear notification badge"""
        self.notification_count = 0

    # Voice command integration

    def handle_voice_command(self, command: str, args: Dict[str, Any]) -> bool:
        """
        Handle voice command directed to this panel.

        Args:
            command: Command name (e.g., "add task", "search files")
            args: Command arguments

        Returns:
            True if command was handled, False if not recognized
        """
        # Default implementation - subclasses override for specific commands
        if command == "focus":
            self.focus_panel()
            return True
        elif command == "minimize":
            self.toggle_minimize()
            return True
        elif command == "clear notifications":
            self.clear_notifications()
            return True

        return False

    # Reactive watchers

    def watch_is_focused(self, is_focused: bool):
        """React to focus state change"""
        self.refresh()

    def watch_is_minimized(self, is_minimized: bool):
        """React to minimize state change"""
        self.refresh()

    def watch_notification_count(self, count: int):
        """React to notification count change"""
        self.refresh()

    # Helper methods

    def get_panel_info(self) -> Dict[str, Any]:
        """
        Get panel information for debugging/logging.

        Returns:
            Dict with panel state
        """
        return {
            "panel_id": self.panel_id,
            "title": self.panel_title,
            "focused": self.is_focused,
            "minimized": self.is_minimized,
            "notifications": self.notification_count,
            "size": (self.size.width, self.size.height),
        }
