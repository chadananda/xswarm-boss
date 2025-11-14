"""
Email tool for sending emails via voice/chat commands.

Integrates PersonaMailer with the tool calling system.
"""

import os
from typing import Dict, Any
from .registry import Tool, ToolParameter
from ..email.persona_mailer import PersonaMailer
from ..personas.manager import PersonaManager


# Global mailer instance (initialized on first use)
_mailer: PersonaMailer | None = None
_persona_manager: PersonaManager | None = None


def get_mailer() -> PersonaMailer:
    """Get or create PersonaMailer instance."""
    global _mailer
    if _mailer is None:
        _mailer = PersonaMailer()
    return _mailer


def get_persona_manager() -> PersonaManager:
    """Get or create PersonaManager instance."""
    global _persona_manager
    if _persona_manager is None:
        _persona_manager = PersonaManager()
    return _persona_manager


async def send_email_handler(
    subject: str,
    content: str,
    include_status_summary: bool = False,
    persona_name: str | None = None,
) -> Dict[str, Any]:
    """
    Tool handler for sending emails.

    Args:
        subject: Email subject
        content: Email content (markdown supported)
        include_status_summary: Whether to include development status
        persona_name: Optional persona name (uses current if not provided)

    Returns:
        Dict with:
            - success: bool
            - message: str
            - message_id: str (if successful)
    """
    try:
        # Get recipient email
        to_email = os.getenv("USER_EMAIL") or os.getenv("XSWARM_DEV_ADMIN_EMAIL")
        if not to_email:
            return {
                "success": False,
                "message": "No recipient email configured. Set USER_EMAIL or XSWARM_DEV_ADMIN_EMAIL environment variable.",
            }

        # Get persona
        persona_manager = get_persona_manager()
        if persona_name:
            persona = persona_manager.load_persona_from_name(persona_name)
        else:
            persona = persona_manager.get_current_persona()

        if not persona:
            return {
                "success": False,
                "message": f"Persona {persona_name or 'current'} not found",
            }

        # Add status summary if requested
        if include_status_summary:
            # TODO: Get actual development status from a status tracker
            status_info = """

---

**Development Status:**

Currently implementing full Moshi voice integration with TUI dashboard, phone capabilities, and email notifications.
"""
            content += status_info

        # Send email
        mailer = get_mailer()
        result = await mailer.send_email(
            to_email=to_email,
            subject=subject,
            content=content,
            persona=persona,
        )

        if result.get("success"):
            return {
                "success": True,
                "message": f"Email sent successfully to {to_email}",
                "message_id": result.get("message_id", ""),
            }
        else:
            return {
                "success": False,
                "message": f"Failed to send email: {result.get('error', 'Unknown error')}",
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error sending email: {str(e)}",
        }


# Tool definition
send_email_tool = Tool(
    name="send_email",
    description="Send an email to the user with a subject and message. Use this when the user asks to be emailed, or when providing status updates.",
    parameters=[
        ToolParameter(
            name="subject",
            type="string",
            description="Email subject line (brief, descriptive)",
            required=True,
        ),
        ToolParameter(
            name="content",
            type="string",
            description="Email body content. Supports basic markdown formatting (** for bold, line breaks, lists).",
            required=True,
        ),
        ToolParameter(
            name="include_status_summary",
            type="boolean",
            description="Whether to include current development status summary in the email",
            required=False,
        ),
    ],
    handler=send_email_handler,
)
