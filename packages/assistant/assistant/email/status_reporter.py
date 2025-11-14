"""
Development status reporter for automated phase completion emails.

Tracks development progress and sends persona-themed status updates.
"""

import os
from typing import Dict, List, Optional
from datetime import datetime
from .persona_mailer import PersonaMailer
from ..personas.config import PersonaConfig


class DevelopmentStatusReporter:
    """Automated development status reporting via email."""

    def __init__(self, persona_mailer: Optional[PersonaMailer] = None):
        """
        Initialize status reporter.

        Args:
            persona_mailer: PersonaMailer instance (creates new one if not provided)
        """
        self.mailer = persona_mailer or PersonaMailer()

    async def send_phase_complete_email(
        self,
        to_email: str,
        phase_number: int,
        phase_name: str,
        accomplishments: List[str],
        files_changed: List[str],
        lines_added: int,
        tests_added: int,
        next_phase: str,
        persona: PersonaConfig,
        verification_notes: str = "",
    ) -> Dict:
        """
        Send phase completion email with development summary.

        Args:
            to_email: Recipient email
            phase_number: Phase number (1-12)
            phase_name: Phase name (e.g., "Voice Bridge Integration")
            accomplishments: List of accomplishments
            files_changed: List of files modified
            lines_added: Number of lines added
            tests_added: Number of tests added
            next_phase: Description of next phase
            persona: Persona to send email as
            verification_notes: Optional verification notes

        Returns:
            Send result dict
        """
        details = {
            "phase_number": phase_number,
            "phase_name": phase_name,
            "accomplishments": accomplishments,
            "files_changed": files_changed,
            "lines_added": lines_added,
            "tests_added": tests_added,
            "next_phase": next_phase,
            "verification_notes": verification_notes,
            "timestamp": datetime.now().isoformat(),
        }

        return await self.mailer.send_status_email(
            to_email=to_email,
            persona=persona,
            status_type="phase_complete",
            details=details,
        )

    async def send_error_notification(
        self,
        to_email: str,
        error_type: str,
        error_message: str,
        phase: str,
        component: str,
        stack_trace: str,
        action_needed: str,
        persona: PersonaConfig,
    ) -> Dict:
        """
        Send error notification email.

        Args:
            to_email: Recipient email
            error_type: Type of error
            error_message: Error message
            phase: Current phase
            component: Component with error
            stack_trace: Full stack trace
            action_needed: What action is needed
            persona: Persona to send email as

        Returns:
            Send result dict
        """
        details = {
            "error_type": error_type,
            "error_message": error_message,
            "phase": phase,
            "component": component,
            "stack_trace": stack_trace,
            "action_needed": action_needed,
            "timestamp": datetime.now().isoformat(),
        }

        return await self.mailer.send_status_email(
            to_email=to_email,
            persona=persona,
            status_type="error",
            details=details,
        )

    async def send_question_email(
        self,
        to_email: str,
        context: str,
        questions: List[str],
        options: str,
        recommendation: str,
        persona: PersonaConfig,
    ) -> Dict:
        """
        Send question email for user feedback.

        Args:
            to_email: Recipient email
            context: Question context
            questions: List of questions
            options: Description of options considered
            recommendation: AI's recommendation
            persona: Persona to send email as

        Returns:
            Send result dict
        """
        details = {
            "context": context,
            "questions": questions,
            "options": options,
            "recommendation": recommendation,
            "topic": questions[0] if questions else "Development Question",
            "timestamp": datetime.now().isoformat(),
        }

        return await self.mailer.send_status_email(
            to_email=to_email,
            persona=persona,
            status_type="question",
            details=details,
        )

    async def send_custom_update(
        self,
        to_email: str,
        subject: str,
        content: str,
        persona: PersonaConfig,
    ) -> Dict:
        """
        Send custom status update email.

        Args:
            to_email: Recipient email
            subject: Email subject
            content: Email content (markdown supported)
            persona: Persona to send email as

        Returns:
            Send result dict
        """
        return await self.mailer.send_email(
            to_email=to_email,
            subject=subject,
            content=content,
            persona=persona,
        )


# Convenience function for quick status emails
async def send_quick_status(
    subject: str,
    message: str,
    persona_name: str = "C-3PO",
    to_email: Optional[str] = None,
) -> Dict:
    """
    Send a quick status email.

    Args:
        subject: Email subject
        message: Email message
        persona_name: Persona to use (default: C-3PO)
        to_email: Recipient (reads from env if not provided)

    Returns:
        Send result dict
    """
    from ..personas.manager import PersonaManager

    # Get recipient email
    if not to_email:
        to_email = os.getenv("USER_EMAIL") or os.getenv("XSWARM_DEV_ADMIN_EMAIL")
        if not to_email:
            return {"success": False, "error": "No recipient email configured"}

    # Load persona
    persona_manager = PersonaManager()
    persona = persona_manager.load_persona_from_name(persona_name)

    if not persona:
        return {"success": False, "error": f"Persona {persona_name} not found"}

    # Send email
    mailer = PersonaMailer()
    return await mailer.send_email(
        to_email=to_email,
        subject=subject,
        content=message,
        persona=persona,
    )
