"""
Meeting Reminder System - State tracking and escalation logic.

Manages meeting reminders with:
- State tracking (sent, acknowledged, escalated)
- Multi-channel notification delivery
- Escalation to SMS/call if not acknowledged
- Deduplication for recurring events
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from .notifications import (
    send_meeting_reminder,
    NotificationChannel,
    NotificationResult
)

logger = logging.getLogger(__name__)


@dataclass
class ReminderState:
    """
    State of a reminder for a specific event instance.

    For recurring events, each occurrence has its own state.
    """
    event_id: str
    event_instance_key: str  # event_id + start_date for uniqueness
    event_title: str
    event_start: str  # ISO format datetime
    reminder_minutes: int = 5

    # Tracking
    reminder_sent_at: Optional[str] = None  # ISO format
    channels_delivered: List[str] = field(default_factory=list)

    # Acknowledgment
    acknowledged_at: Optional[str] = None  # ISO format
    acknowledged_via: Optional[str] = None  # "tui", "voice", etc.

    # Escalation
    escalation_level: int = 0  # 0=none, 1=sms, 2=call
    escalated_at: Optional[str] = None  # ISO format

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReminderState":
        """Create from dictionary."""
        return cls(**data)


class ReminderManager:
    """
    Manages meeting reminders with state persistence.

    Features:
    - Tracks reminder state (sent, acknowledged, escalated)
    - Delivers reminders through multiple channels
    - Escalates to SMS/call if not acknowledged
    - Handles recurring events correctly
    - Persists state to disk
    """

    def __init__(
        self,
        state_file: Optional[Path] = None,
        escalation_enabled: bool = True,
        escalation_delay_minutes: int = 2,
        sms_callback: Optional[Callable[[str, str], bool]] = None,
        call_callback: Optional[Callable[[str, str], bool]] = None
    ):
        """
        Initialize the reminder manager.

        Args:
            state_file: Path to state persistence file
            escalation_enabled: Whether to escalate to SMS/call
            escalation_delay_minutes: Minutes to wait before escalating
            sms_callback: Function to send SMS (phone_number, message) -> success
            call_callback: Function to make call (phone_number, message) -> success
        """
        self.state_file = state_file or Path.home() / ".xswarm" / "reminder_states.json"
        self.escalation_enabled = escalation_enabled
        self.escalation_delay_minutes = escalation_delay_minutes
        self.sms_callback = sms_callback
        self.call_callback = call_callback

        # In-memory state cache
        self._states: Dict[str, ReminderState] = {}
        self._load_states()

    def _load_states(self) -> None:
        """Load reminder states from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    for key, state_data in data.items():
                        self._states[key] = ReminderState.from_dict(state_data)
                logger.debug(f"Loaded {len(self._states)} reminder states")
            except Exception as e:
                logger.error(f"Failed to load reminder states: {e}")
                self._states = {}

    def _save_states(self) -> None:
        """Save reminder states to disk."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                data = {key: state.to_dict() for key, state in self._states.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save reminder states: {e}")

    def _make_instance_key(self, event_id: str, start_time: str) -> str:
        """
        Create a unique key for an event instance.

        For recurring events, the same event_id will have different
        start times, so we combine them for uniqueness.
        """
        # Extract date from start_time (first 10 chars of ISO format)
        date_part = start_time[:10] if len(start_time) >= 10 else start_time
        return f"{event_id}_{date_part}"

    def get_or_create_state(
        self,
        event_id: str,
        event_title: str,
        event_start: str,
        reminder_minutes: int = 5
    ) -> ReminderState:
        """
        Get existing state or create new one for an event instance.

        Args:
            event_id: Event ID
            event_title: Event title
            event_start: Event start time (ISO format)
            reminder_minutes: Minutes before event to remind

        Returns:
            ReminderState for this event instance
        """
        key = self._make_instance_key(event_id, event_start)

        if key not in self._states:
            self._states[key] = ReminderState(
                event_id=event_id,
                event_instance_key=key,
                event_title=event_title,
                event_start=event_start,
                reminder_minutes=reminder_minutes
            )
            self._save_states()

        return self._states[key]

    def should_send_reminder(
        self,
        event_id: str,
        event_start: str,
        reminder_minutes: int = 5
    ) -> bool:
        """
        Check if a reminder should be sent for this event.

        Args:
            event_id: Event ID
            event_start: Event start time (ISO format)
            reminder_minutes: Minutes before event to remind

        Returns:
            True if reminder should be sent now
        """
        key = self._make_instance_key(event_id, event_start)
        state = self._states.get(key)

        # Already sent
        if state and state.reminder_sent_at:
            return False

        # Parse event start time
        try:
            start_dt = datetime.fromisoformat(event_start.replace("Z", "+00:00"))
            if start_dt.tzinfo:
                start_dt = start_dt.replace(tzinfo=None)
        except ValueError:
            logger.error(f"Invalid event start time: {event_start}")
            return False

        now = datetime.now()
        time_until = start_dt - now
        minutes_until = time_until.total_seconds() / 60

        # Time to remind?
        return 0 <= minutes_until <= reminder_minutes

    def send_reminder(
        self,
        event_id: str,
        event_title: str,
        event_start: str,
        reminder_minutes: int = 5,
        voice: str = "Alex"
    ) -> Dict[str, NotificationResult]:
        """
        Send a reminder for an event through all channels.

        Args:
            event_id: Event ID
            event_title: Event title
            event_start: Event start time (ISO format)
            reminder_minutes: Minutes before event
            voice: Voice for spoken announcement

        Returns:
            Dict of channel -> NotificationResult
        """
        state = self.get_or_create_state(
            event_id, event_title, event_start, reminder_minutes
        )

        # Calculate minutes until event
        try:
            start_dt = datetime.fromisoformat(event_start.replace("Z", "+00:00"))
            if start_dt.tzinfo:
                start_dt = start_dt.replace(tzinfo=None)
            minutes_until = int((start_dt - datetime.now()).total_seconds() / 60)
        except ValueError:
            minutes_until = reminder_minutes

        # Send through all standard channels
        results = send_meeting_reminder(
            title=event_title,
            minutes_until=minutes_until,
            voice=voice
        )

        # Update state
        state.reminder_sent_at = datetime.now().isoformat()
        state.channels_delivered = list(results.keys())
        self._save_states()

        logger.info(f"Sent reminder for '{event_title}' ({minutes_until} min before)")
        return results

    def acknowledge(
        self,
        event_id: str,
        event_start: str,
        via: str = "tui"
    ) -> bool:
        """
        Acknowledge a reminder (prevents escalation).

        Args:
            event_id: Event ID
            event_start: Event start time (ISO format)
            via: How the reminder was acknowledged

        Returns:
            True if state was updated
        """
        key = self._make_instance_key(event_id, event_start)
        state = self._states.get(key)

        if not state:
            return False

        state.acknowledged_at = datetime.now().isoformat()
        state.acknowledged_via = via
        self._save_states()

        logger.info(f"Reminder acknowledged for event {event_id} via {via}")
        return True

    def check_escalation(
        self,
        event_id: str,
        event_start: str,
        phone_number: Optional[str] = None
    ) -> Optional[str]:
        """
        Check if reminder should be escalated and do so if needed.

        Args:
            event_id: Event ID
            event_start: Event start time (ISO format)
            phone_number: User's phone number for SMS/call

        Returns:
            Escalation action taken ("sms", "call") or None
        """
        if not self.escalation_enabled:
            return None

        key = self._make_instance_key(event_id, event_start)
        state = self._states.get(key)

        if not state or not state.reminder_sent_at or state.acknowledged_at:
            return None

        # Calculate time since reminder was sent
        sent_at = datetime.fromisoformat(state.reminder_sent_at)
        time_since = datetime.now() - sent_at
        minutes_since = time_since.total_seconds() / 60

        # Check escalation thresholds
        if minutes_since >= self.escalation_delay_minutes:
            if state.escalation_level == 0 and self.sms_callback and phone_number:
                # Escalate to SMS
                message = f"Reminder: {state.event_title} is starting soon!"
                try:
                    success = self.sms_callback(phone_number, message)
                    if success:
                        state.escalation_level = 1
                        state.escalated_at = datetime.now().isoformat()
                        self._save_states()
                        logger.info(f"Escalated to SMS for {state.event_title}")
                        return "sms"
                except Exception as e:
                    logger.error(f"SMS escalation failed: {e}")

            elif state.escalation_level == 1 and minutes_since >= self.escalation_delay_minutes * 2:
                if self.call_callback and phone_number:
                    # Escalate to call
                    message = f"This is a reminder that {state.event_title} is starting now."
                    try:
                        success = self.call_callback(phone_number, message)
                        if success:
                            state.escalation_level = 2
                            state.escalated_at = datetime.now().isoformat()
                            self._save_states()
                            logger.info(f"Escalated to call for {state.event_title}")
                            return "call"
                    except Exception as e:
                        logger.error(f"Call escalation failed: {e}")

        return None

    def cleanup_old_states(self, hours: int = 1) -> int:
        """
        Remove states for events that have passed.

        Args:
            hours: Hours after event start to keep state

        Returns:
            Number of states removed
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        to_remove = []

        for key, state in self._states.items():
            try:
                start_dt = datetime.fromisoformat(state.event_start.replace("Z", "+00:00"))
                if start_dt.tzinfo:
                    start_dt = start_dt.replace(tzinfo=None)
                if start_dt < cutoff:
                    to_remove.append(key)
            except ValueError:
                continue

        for key in to_remove:
            del self._states[key]

        if to_remove:
            self._save_states()
            logger.debug(f"Cleaned up {len(to_remove)} old reminder states")

        return len(to_remove)

    def check_reminders(
        self,
        events: List[Dict[str, Any]],
        phone_number: Optional[str] = None,
        voice: str = "Alex"
    ) -> List[str]:
        """
        Check all events and send/escalate reminders as needed.

        This is the main entry point called by the scheduler.

        Args:
            events: List of calendar events with id, title, start_time, reminder_minutes
            phone_number: User's phone number for escalation
            voice: Voice for spoken reminders

        Returns:
            List of actions taken (e.g., ["sent:event1", "escalated:event2"])
        """
        actions = []

        for event in events:
            event_id = event.get("id", "")
            event_title = event.get("title", "Meeting")
            event_start = event.get("start_time", "")
            reminder_minutes = event.get("reminder_minutes", 5)

            if not event_id or not event_start:
                continue

            # Check if we should send reminder
            if self.should_send_reminder(event_id, event_start, reminder_minutes):
                self.send_reminder(
                    event_id, event_title, event_start,
                    reminder_minutes, voice
                )
                actions.append(f"sent:{event_id}")

            # Check escalation
            escalation = self.check_escalation(event_id, event_start, phone_number)
            if escalation:
                actions.append(f"escalated_{escalation}:{event_id}")

        # Cleanup old states
        self.cleanup_old_states()

        return actions


# Global reminder manager instance
_reminder_manager: Optional[ReminderManager] = None


def get_reminder_manager() -> ReminderManager:
    """Get or create the global reminder manager instance."""
    global _reminder_manager
    if _reminder_manager is None:
        _reminder_manager = ReminderManager()
    return _reminder_manager


def set_reminder_manager(manager: ReminderManager) -> None:
    """Set the global reminder manager instance."""
    global _reminder_manager
    _reminder_manager = manager
