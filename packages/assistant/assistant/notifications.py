"""
Notification System - Multi-channel notification delivery.

Provides various notification channels:
- macOS native notifications (via osascript)
- Sound alerts (via afplay)
- Voice announcements (via say command)
- TUI toast notifications (via Textual app.notify)

For SMS and phone calls, see phone.py (Twilio integration).
"""

import logging
import platform
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Available notification channels."""
    TUI = "tui"           # Textual app toast
    MACOS = "macos"       # macOS native notification
    SOUND = "sound"       # Audio alert
    VOICE = "voice"       # Spoken announcement
    SMS = "sms"           # Twilio SMS (via phone.py)
    CALL = "call"         # Twilio voice call (via phone.py)


@dataclass
class NotificationResult:
    """Result of a notification attempt."""
    channel: NotificationChannel
    success: bool
    error: Optional[str] = None


def send_macos_notification(
    title: str,
    message: str,
    sound: str = "default",
    subtitle: Optional[str] = None
) -> NotificationResult:
    """
    Send a macOS native notification via osascript.

    Args:
        title: Notification title
        message: Notification body
        sound: Sound name (default, Glass, Ping, etc.) or empty for silent
        subtitle: Optional subtitle

    Returns:
        NotificationResult indicating success/failure
    """
    if platform.system() != "Darwin":
        return NotificationResult(
            channel=NotificationChannel.MACOS,
            success=False,
            error="Not running on macOS"
        )

    # Build the AppleScript command
    # Escape quotes in the message
    title_escaped = title.replace('"', '\\"')
    message_escaped = message.replace('"', '\\"')

    script_parts = [f'display notification "{message_escaped}"']
    script_parts.append(f'with title "{title_escaped}"')

    if subtitle:
        subtitle_escaped = subtitle.replace('"', '\\"')
        script_parts.append(f'subtitle "{subtitle_escaped}"')

    if sound:
        script_parts.append(f'sound name "{sound}"')

    script = " ".join(script_parts)

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        logger.debug(f"macOS notification sent: {title}")
        return NotificationResult(channel=NotificationChannel.MACOS, success=True)
    except subprocess.CalledProcessError as e:
        error_msg = f"osascript failed: {e.stderr}"
        logger.error(error_msg)
        return NotificationResult(
            channel=NotificationChannel.MACOS,
            success=False,
            error=error_msg
        )
    except subprocess.TimeoutExpired:
        return NotificationResult(
            channel=NotificationChannel.MACOS,
            success=False,
            error="Notification timed out"
        )


def play_sound(sound_name: str = "Glass") -> NotificationResult:
    """
    Play a system sound on macOS.

    Args:
        sound_name: Name of system sound (Glass, Ping, Pop, Purr, etc.)
                   or path to audio file

    Returns:
        NotificationResult indicating success/failure
    """
    if platform.system() != "Darwin":
        return NotificationResult(
            channel=NotificationChannel.SOUND,
            success=False,
            error="Not running on macOS"
        )

    # Check if it's a path or a system sound name
    sound_path = Path(sound_name)
    if sound_path.exists():
        file_to_play = str(sound_path)
    else:
        # Try system sounds directory
        system_sound = Path(f"/System/Library/Sounds/{sound_name}.aiff")
        if system_sound.exists():
            file_to_play = str(system_sound)
        else:
            # Fallback to Glass
            file_to_play = "/System/Library/Sounds/Glass.aiff"

    try:
        subprocess.run(
            ["afplay", file_to_play],
            check=True,
            capture_output=True,
            timeout=10
        )
        logger.debug(f"Sound played: {file_to_play}")
        return NotificationResult(channel=NotificationChannel.SOUND, success=True)
    except subprocess.CalledProcessError as e:
        error_msg = f"afplay failed: {e}"
        logger.error(error_msg)
        return NotificationResult(
            channel=NotificationChannel.SOUND,
            success=False,
            error=error_msg
        )
    except subprocess.TimeoutExpired:
        return NotificationResult(
            channel=NotificationChannel.SOUND,
            success=False,
            error="Sound playback timed out"
        )


def speak_text(
    text: str,
    voice: str = "Alex",
    rate: int = 200
) -> NotificationResult:
    """
    Speak text using macOS text-to-speech.

    Args:
        text: Text to speak
        voice: macOS voice name (Alex, Samantha, Daniel, etc.)
        rate: Speech rate in words per minute

    Returns:
        NotificationResult indicating success/failure
    """
    if platform.system() != "Darwin":
        return NotificationResult(
            channel=NotificationChannel.VOICE,
            success=False,
            error="Not running on macOS"
        )

    try:
        subprocess.run(
            ["say", "-v", voice, "-r", str(rate), text],
            check=True,
            capture_output=True,
            timeout=30
        )
        logger.debug(f"Spoke: {text[:50]}...")
        return NotificationResult(channel=NotificationChannel.VOICE, success=True)
    except subprocess.CalledProcessError as e:
        error_msg = f"say command failed: {e}"
        logger.error(error_msg)
        return NotificationResult(
            channel=NotificationChannel.VOICE,
            success=False,
            error=error_msg
        )
    except subprocess.TimeoutExpired:
        return NotificationResult(
            channel=NotificationChannel.VOICE,
            success=False,
            error="Speech timed out"
        )


def speak_reminder(
    title: str,
    minutes_until: int,
    voice: str = "Alex"
) -> NotificationResult:
    """
    Speak a meeting reminder announcement.

    Args:
        title: Meeting/event title
        minutes_until: Minutes until the event starts
        voice: macOS voice name

    Returns:
        NotificationResult indicating success/failure
    """
    if minutes_until <= 0:
        message = f"Reminder: {title} is starting now"
    elif minutes_until == 1:
        message = f"Reminder: {title} starts in 1 minute"
    else:
        message = f"Reminder: {title} starts in {minutes_until} minutes"

    return speak_text(message, voice=voice)


# TUI notification callback holder
_tui_notify_callback: Optional[Callable[[str, str], None]] = None


def set_tui_notify_callback(callback: Callable[[str, str], None]) -> None:
    """
    Set the callback for TUI notifications.

    This should be called by the dashboard app to wire up notifications.
    The callback receives (message, title) arguments.
    """
    global _tui_notify_callback
    _tui_notify_callback = callback
    logger.debug("TUI notification callback registered")


def send_tui_notification(
    message: str,
    title: str = "Notification"
) -> NotificationResult:
    """
    Send a TUI toast notification.

    Args:
        message: Notification message
        title: Notification title

    Returns:
        NotificationResult indicating success/failure
    """
    global _tui_notify_callback

    if _tui_notify_callback is None:
        return NotificationResult(
            channel=NotificationChannel.TUI,
            success=False,
            error="TUI notification callback not registered"
        )

    try:
        _tui_notify_callback(message, title)
        logger.debug(f"TUI notification: {title} - {message}")
        return NotificationResult(channel=NotificationChannel.TUI, success=True)
    except Exception as e:
        error_msg = f"TUI notification failed: {e}"
        logger.error(error_msg)
        return NotificationResult(
            channel=NotificationChannel.TUI,
            success=False,
            error=error_msg
        )


def send_meeting_reminder(
    title: str,
    minutes_until: int,
    channels: Optional[list] = None,
    voice: str = "Alex"
) -> dict:
    """
    Send a meeting reminder through multiple channels.

    Args:
        title: Meeting/event title
        minutes_until: Minutes until the event starts
        channels: List of channels to use (default: all available)
        voice: Voice for spoken announcement

    Returns:
        Dict mapping channel names to NotificationResult
    """
    if channels is None:
        channels = [
            NotificationChannel.TUI,
            NotificationChannel.MACOS,
            NotificationChannel.SOUND,
            NotificationChannel.VOICE
        ]

    results = {}

    # Format the message
    if minutes_until <= 0:
        time_str = "starting now"
    elif minutes_until == 1:
        time_str = "in 1 minute"
    else:
        time_str = f"in {minutes_until} minutes"

    message = f"{title} {time_str}"

    for channel in channels:
        if channel == NotificationChannel.TUI:
            results[channel.value] = send_tui_notification(
                f"📅 {message}",
                title="Meeting Reminder"
            )
        elif channel == NotificationChannel.MACOS:
            results[channel.value] = send_macos_notification(
                title="Meeting Reminder",
                message=message,
                sound="Glass"
            )
        elif channel == NotificationChannel.SOUND:
            results[channel.value] = play_sound("Glass")
        elif channel == NotificationChannel.VOICE:
            results[channel.value] = speak_reminder(title, minutes_until, voice)

    return results
