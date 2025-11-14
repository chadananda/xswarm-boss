"""
Phone tool for making calls via voice/chat commands.

Integrates OutboundCaller with the tool calling system.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
import toml
from .registry import Tool, ToolParameter
from ..phone.outbound_caller import OutboundCaller
from ..personas.manager import PersonaManager


# Global caller instance (initialized on first use)
_caller: OutboundCaller | None = None
_persona_manager: PersonaManager | None = None


def get_caller() -> OutboundCaller:
    """Get or create OutboundCaller instance."""
    global _caller
    if _caller is None:
        _caller = OutboundCaller()
    return _caller


def get_persona_manager() -> PersonaManager:
    """Get or create PersonaManager instance."""
    global _persona_manager
    if _persona_manager is None:
        personas_dir = Path(__file__).parent.parent.parent.parent / "personas"
        _persona_manager = PersonaManager(personas_dir=personas_dir)
    return _persona_manager


async def make_call_handler(
    message: str,
    questions: Optional[list] = None,
    persona_name: str | None = None,
) -> Dict[str, Any]:
    """
    Tool handler for making phone calls.

    Args:
        message: Message to speak to the user
        questions: Optional list of questions to ask (max 3)
        persona_name: Optional persona name (uses current if not provided)

    Returns:
        Dict with:
            - success: bool
            - message: str
            - call_sid: str (if successful)
    """
    try:
        # Get recipient phone number
        to_number = os.getenv("USER_PHONE") or os.getenv("XSWARM_DEV_ADMIN_PHONE")
        if not to_number:
            # Try config.toml admin.phone
            config_path = Path.home().parent.parent / "Dropbox/Public/JS/Projects/xswarm-boss/config.toml"
            if not config_path.exists():
                config_path = Path("config.toml")
            if config_path.exists():
                config = toml.load(config_path)
                to_number = config.get("admin", {}).get("phone")
        if not to_number:
            return {
                "success": False,
                "message": "No phone number configured. Set USER_PHONE, XSWARM_DEV_ADMIN_PHONE, or admin.phone in config.toml",
            }

        # Get persona
        persona_manager = get_persona_manager()
        if persona_name:
            persona = persona_manager.get_persona(persona_name)
        else:
            persona = persona_manager.get_current_persona()

        if not persona:
            return {
                "success": False,
                "message": f"Persona {persona_name or 'current'} not found",
            }

        # Limit questions to 3
        if questions and len(questions) > 3:
            questions = questions[:3]

        # Make call
        caller = get_caller()
        result = await caller.make_call(
            to_number=to_number,
            message=message,
            persona=persona,
            questions=questions,
        )

        if result.get("success"):
            return {
                "success": True,
                "message": f"Call initiated to {to_number} as {persona.name}",
                "call_sid": result.get("call_sid", ""),
                "status": result.get("status", ""),
            }
        else:
            return {
                "success": False,
                "message": f"Failed to make call: {result.get('error', 'Unknown error')}",
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error making call: {str(e)}",
        }


async def feedback_call_handler(
    phase_number: int,
    phase_name: str,
    next_steps: str,
    questions: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Tool handler for making feedback calls about development status.

    Args:
        phase_number: Phase number (1-12)
        phase_name: Phase name (e.g., "Voice Bridge Integration")
        next_steps: Description of next steps
        questions: Optional list of questions (max 3)

    Returns:
        Dict with success status and call details
    """
    try:
        # Get recipient phone number
        to_number = os.getenv("USER_PHONE") or os.getenv("XSWARM_DEV_ADMIN_PHONE")
        if not to_number:
            # Try config.toml admin.phone
            config_path = Path.home().parent.parent / "Dropbox/Public/JS/Projects/xswarm-boss/config.toml"
            if not config_path.exists():
                config_path = Path("config.toml")
            if config_path.exists():
                config = toml.load(config_path)
                to_number = config.get("admin", {}).get("phone")
        if not to_number:
            return {
                "success": False,
                "message": "No phone number configured",
            }

        # Get C-3PO persona (default for feedback calls)
        persona_manager = get_persona_manager()
        persona = persona_manager.get_persona("C-3PO")

        if not persona:
            return {
                "success": False,
                "message": "C-3PO persona not found",
            }

        # Default questions if not provided
        if not questions:
            questions = [
                "Would you like me to continue with the next phase?",
                "Are there any changes to priorities?",
                "Do you need a detailed status email?",
            ]

        # Limit to 3 questions
        if len(questions) > 3:
            questions = questions[:3]

        # Make feedback call
        caller = get_caller()
        phase_info = {
            "phase_number": phase_number,
            "phase_name": phase_name,
            "next_steps": next_steps,
            "questions": questions,
        }

        result = await caller.make_feedback_call(
            to_number=to_number,
            persona=persona,
            phase_info=phase_info,
        )

        if result.get("success"):
            return {
                "success": True,
                "message": f"Feedback call initiated to {to_number}",
                "call_sid": result.get("call_sid", ""),
            }
        else:
            return {
                "success": False,
                "message": f"Failed to make feedback call: {result.get('error', 'Unknown error')}",
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error making feedback call: {str(e)}",
        }


# Tool definitions
make_call_tool = Tool(
    name="make_call",
    description="Make a phone call to the user with a message. Use this when you need to contact the user urgently or for important updates.",
    parameters=[
        ToolParameter(
            name="message",
            type="string",
            description="Message to speak to the user (keep concise, 1-2 sentences)",
            required=True,
        ),
        ToolParameter(
            name="questions",
            type="array",
            description="Optional list of questions to ask (max 3 questions). User will record voice responses.",
            required=False,
        ),
        ToolParameter(
            name="persona_name",
            type="string",
            description="Optional persona name to use for the call (default: current persona)",
            required=False,
        ),
    ],
    handler=make_call_handler,
)

feedback_call_tool = Tool(
    name="call_for_feedback",
    description="Make a development feedback call to the user about completed phases and next steps.",
    parameters=[
        ToolParameter(
            name="phase_number",
            type="number",
            description="Phase number that was completed (1-12)",
            required=True,
        ),
        ToolParameter(
            name="phase_name",
            type="string",
            description="Name of the completed phase",
            required=True,
        ),
        ToolParameter(
            name="next_steps",
            type="string",
            description="Description of what will be done in the next phase",
            required=True,
        ),
        ToolParameter(
            name="questions",
            type="array",
            description="Optional list of specific questions to ask (max 3)",
            required=False,
        ),
    ],
    handler=feedback_call_handler,
)
