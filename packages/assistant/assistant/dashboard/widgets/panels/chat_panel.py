"""
Chat panel for conversation with AI assistant.

Displays message history, handles user input, and shows voice activity.
"""

from collections import deque
from typing import Deque, Dict, Any, List, Tuple
from datetime import datetime
from textual.widgets import Static
from rich.text import Text
from .panel_base import PanelBase


class Message:
    """Represents a chat message."""

    def __init__(self, role: str, content: str, timestamp: datetime = None):
        """
        Initialize message.

        Args:
            role: 'user' or 'assistant'
            content: Message text
            timestamp: When message was sent (defaults to now)
        """
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()

    def __repr__(self):
        return f"Message(role={self.role}, content={self.content[:30]}...)"


class ChatPanel(PanelBase):
    """
    Chat panel for AI conversation.

    Features:
    - Scrollable message history
    - User messages (right-aligned, cyan)
    - AI messages (left-aligned, green)
    - Voice activity indicator
    - Typing indicator
    - Quick command hints
    """

    def __init__(
        self,
        max_messages: int = 100,
        **kwargs
    ):
        """
        Initialize chat panel.

        Args:
            max_messages: Maximum messages to keep in history
        """
        super().__init__(
            panel_id="chat",
            title="Chat",
            min_width=40,
            min_height=15,
            **kwargs
        )
        self.messages: Deque[Message] = deque(maxlen=max_messages)
        self.is_listening = False
        self.is_typing = False
        self.current_input = ""

    def add_message(self, role: str, content: str):
        """
        Add a message to chat history.

        Args:
            role: 'user' or 'assistant'
            content: Message text
        """
        message = Message(role=role, content=content)
        self.messages.append(message)

        # Clear notifications when viewing chat
        if self.is_focused:
            self.clear_notifications()
        else:
            # Increment notification count if not focused
            self.increment_notification()

        self.refresh()

    def render_content(self) -> Text:
        """
        Render chat messages and input area.

        Returns:
            Rich Text with chat content
        """
        result = Text()

        # Calculate available space
        widget_width = max(self.size.width, self.min_width)
        widget_height = max(self.size.height, self.min_height)
        content_width = widget_width - 4  # Account for borders
        available_lines = widget_height - 2  # Account for borders

        # Reserve lines for footer
        footer_lines = 3  # Voice indicator + input box + divider
        message_lines = available_lines - footer_lines

        # Render messages (bottom-up, most recent at bottom)
        lines: List[str] = []

        if not self.messages:
            # Show welcome message if no messages
            lines.append("")
            lines.append("  Welcome! Start chatting or use voice commands.")
            lines.append("")
        else:
            # Render messages from most recent, working backwards
            for message in reversed(list(self.messages)):
                msg_lines = self._format_message(message, content_width)
                lines.extend(reversed(msg_lines))
                lines.append("")  # Blank line between messages

                # Stop if we've filled available space
                if len(lines) >= message_lines:
                    break

            # Reverse to show oldest first
            lines = list(reversed(lines))

        # Trim to available space
        lines = lines[-message_lines:]

        # Pad if needed
        while len(lines) < message_lines:
            lines.insert(0, "")

        # Add message lines
        for line in lines:
            result.append(line + "\n")

        # Add divider
        result.append("─" * content_width + "\n", style="dim cyan")

        # Voice activity indicator
        if self.is_listening:
            result.append("🎤 Listening... ", style="bold yellow")
        elif self.is_typing:
            result.append("💬 AI is typing... ", style="dim green")
        else:
            result.append("💬 Ready ", style="dim white")

        result.append("\n")

        # Input preview
        if self.current_input:
            input_display = self.current_input[:content_width - 4]
            result.append(f"> {input_display}", style="cyan")
        else:
            result.append("> Type or speak...", style="dim white")

        return result

    def _format_message(self, message: Message, width: int) -> List[str]:
        """
        Format a message for display.

        Args:
            message: Message to format
            width: Available width for content

        Returns:
            List of formatted lines
        """
        lines = []

        # Timestamp
        time_str = message.timestamp.strftime("%H:%M")

        if message.role == "user":
            # User messages: right-aligned, cyan
            # Format: "[19:30] User: message text here"
            prefix = f"[{time_str}] You: "
            style = "cyan"

            # Word wrap
            content_width = width - len(prefix)
            wrapped = self._wrap_text(message.content, content_width)

            for i, line in enumerate(wrapped):
                if i == 0:
                    lines.append(f"{prefix}{line}")
                else:
                    lines.append(" " * len(prefix) + line)

        else:
            # Assistant messages: left-aligned, green
            # Format: "[19:30] AI: message text here"
            prefix = f"[{time_str}] AI: "
            style = "green"

            # Word wrap
            content_width = width - len(prefix)
            wrapped = self._wrap_text(message.content, content_width)

            for i, line in enumerate(wrapped):
                if i == 0:
                    lines.append(f"{prefix}{line}")
                else:
                    lines.append(" " * len(prefix) + line)

        return lines

    def _wrap_text(self, text: str, width: int) -> List[str]:
        """
        Wrap text to fit within width.

        Args:
            text: Text to wrap
            width: Maximum line width

        Returns:
            List of wrapped lines
        """
        if width <= 0:
            return [text]

        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_length = len(word)

            # Check if adding word would exceed width
            if current_length + word_length + len(current_line) > width:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                    current_length = word_length
                else:
                    # Single word longer than width - truncate
                    lines.append(word[:width])
                    current_line = []
                    current_length = 0
            else:
                current_line.append(word)
                current_length += word_length

        # Add remaining words
        if current_line:
            lines.append(" ".join(current_line))

        return lines if lines else [""]

    def set_listening(self, listening: bool):
        """
        Set voice listening state.

        Args:
            listening: True if listening for voice input
        """
        self.is_listening = listening
        self.refresh()

    def set_typing(self, typing: bool):
        """
        Set AI typing state.

        Args:
            typing: True if AI is generating response
        """
        self.is_typing = typing
        self.refresh()

    def set_input(self, text: str):
        """
        Set current input text.

        Args:
            text: Current input text
        """
        self.current_input = text
        self.refresh()

    def clear_input(self):
        """Clear input text."""
        self.current_input = ""
        self.refresh()

    def handle_voice_command(self, command: str, args: Dict[str, Any]) -> bool:
        """
        Handle voice command directed to chat panel.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            True if command was handled
        """
        # Handle base commands (focus, minimize, etc.)
        if super().handle_voice_command(command, args):
            return True

        # Chat-specific commands
        if command == "clear chat":
            self.messages.clear()
            self.refresh()
            return True

        elif command == "scroll up":
            # TODO: Implement scrolling when we add scroll support
            return True

        elif command == "scroll down":
            # TODO: Implement scrolling when we add scroll support
            return True

        elif command == "copy last message":
            if self.messages:
                last_msg = self.messages[-1]
                # TODO: Copy to clipboard
                return True

        return False

    def get_panel_info(self) -> Dict[str, Any]:
        """
        Get panel information for debugging.

        Returns:
            Dict with panel state
        """
        info = super().get_panel_info()
        info.update({
            "message_count": len(self.messages),
            "is_listening": self.is_listening,
            "is_typing": self.is_typing,
            "has_input": bool(self.current_input),
        })
        return info
