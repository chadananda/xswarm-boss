"""
Outbound calling with Twilio API.

Makes phone calls using Twilio's REST API with TwiML for voice prompts.
"""

import os
from typing import Dict, Optional
from pathlib import Path
import toml
from twilio.rest import Client
from ..personas.config import PersonaConfig


class OutboundCaller:
    """Make outbound phone calls with persona-aware voice prompts."""

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
    ):
        """
        Initialize OutboundCaller with Twilio credentials.

        Args:
            account_sid: Twilio account SID (reads from config if not provided)
            auth_token: Twilio auth token (reads from env if not provided)
            from_number: From phone number (reads from config if not provided)
        """
        # Get credentials from environment variables first, then fall back to config
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")

        # Get from number from environment
        if from_number:
            self.from_number = from_number
        else:
            self.from_number = os.getenv("TWILIO_PHONE_NUMBER") or os.getenv("ADMIN_ASSISTANT_PHONE_NUMBER")

        # Fall back to config if env vars not set
        if not self.account_sid or not self.auth_token or not self.from_number:
            config_path = Path.home().parent.parent / "Dropbox/Public/JS/Projects/xswarm-boss/config.toml"
            if not config_path.exists():
                config_path = Path("config.toml")

            config = toml.load(config_path) if config_path.exists() else {}

            if not self.account_sid:
                self.account_sid = config.get("twilio", {}).get("account_sid")
            if not self.auth_token:
                self.auth_token = config.get("twilio", {}).get("auth_token")
            if not self.from_number:
                self.from_number = config.get("twilio", {}).get("phone_number", "+15551234567")

        if not self.account_sid or not self.auth_token:
            raise ValueError("Twilio credentials not found in environment or config.toml")

        if not self.from_number:
            raise ValueError("Twilio phone number not found in environment or config.toml")

        # Initialize Twilio client
        self.client = Client(self.account_sid, self.auth_token)

    def _generate_twiml_for_persona(
        self,
        persona: PersonaConfig,
        message: str,
        questions: Optional[list] = None,
    ) -> str:
        """
        Generate TwiML for persona-specific voice call.

        Args:
            persona: Persona configuration
            message: Message to speak
            questions: Optional list of questions to ask

        Returns:
            TwiML XML string
        """
        # Voice mapping for personas (Twilio Polly voices)
        voice_map = {
            "C-3PO": "Polly.Brian-Neural",  # British English, formal
            "JARVIS": "Polly.Matthew-Neural",  # US English, sophisticated
            "GLaDOS": "Polly.Joanna-Neural",  # US English, calm/clinical
            "HAL 9000": "Polly.Matthew-Neural",  # US English, calm
            "TARS": "Polly.Joey-Neural",  # US English, straightforward
            "KITT": "Polly.Matthew-Neural",  # US English, authoritative
            "Marvin": "Polly.Brian-Neural",  # British English, deadpan
        }
        voice = voice_map.get(persona.name, "Polly.Matthew-Neural")

        # Start TwiML
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="{voice}">{message}</Say>"""

        # Add questions if provided
        if questions:
            for i, question in enumerate(questions):
                twiml += f"""
    <Say voice="{voice}">{question}</Say>
    <Record maxLength="30" timeout="3" transcribe="true" recordingStatusCallback="/api/twilio/recording-callback" />"""

        # End call
        twiml += """
    <Say voice="{voice}">Thank you. Goodbye.</Say>
    <Hangup/>
</Response>"""

        return twiml

    async def make_call(
        self,
        to_number: str,
        message: str,
        persona: PersonaConfig,
        questions: Optional[list] = None,
        twiml_url: Optional[str] = None,
    ) -> Dict:
        """
        Make an outbound call with persona voice.

        Args:
            to_number: Phone number to call (E.164 format)
            message: Message to speak
            persona: Persona configuration
            questions: Optional list of questions to ask
            twiml_url: Optional TwiML URL (generates inline TwiML if not provided)

        Returns:
            Dict with:
                - success: bool
                - call_sid: str (if successful)
                - error: str (if failed)
        """
        try:
            # Generate TwiML if URL not provided
            if twiml_url:
                twiml = None
                url = twiml_url
            else:
                twiml = self._generate_twiml_for_persona(persona, message, questions)
                url = None

            # Make call
            if twiml:
                # Use inline TwiML
                call = self.client.calls.create(
                    to=to_number,
                    from_=self.from_number,
                    twiml=twiml,
                )
            else:
                # Use TwiML URL
                call = self.client.calls.create(
                    to=to_number,
                    from_=self.from_number,
                    url=url,
                )

            return {
                "success": True,
                "call_sid": call.sid,
                "status": call.status,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def make_feedback_call(
        self,
        to_number: str,
        persona: PersonaConfig,
        phase_info: Dict,
    ) -> Dict:
        """
        Make a feedback call for development status.

        Args:
            to_number: Phone number to call
            persona: Persona configuration
            phase_info: Dict with phase details (phase_number, phase_name, next_steps)

        Returns:
            Call result dict
        """
        # C-3PO-specific greeting
        if persona.name == "C-3PO":
            greeting = f"Oh my! Hello there. This is {persona.name} calling with an important update."
            status = f"I have just completed Phase {phase_info.get('phase_number', '?')}: {phase_info.get('phase_name', 'Development Update')}."
            next_info = f"The next phase will involve {phase_info.get('next_steps', 'additional development work')}."
            questions_prompt = "I have a few questions about how you would like me to proceed."
        else:
            greeting = f"This is {persona.name}. Calling with a development update."
            status = f"Phase {phase_info.get('phase_number', '?')} complete: {phase_info.get('phase_name', 'Update')}."
            next_info = f"Next: {phase_info.get('next_steps', 'TBD')}."
            questions_prompt = "Questions for you:"

        message = f"{greeting} {status} {next_info} {questions_prompt}"

        questions = phase_info.get("questions", [
            "Would you like me to continue with the next phase?",
            "Are there any changes to priorities?",
            "Do you need a detailed status email?",
        ])

        return await self.make_call(
            to_number=to_number,
            message=message,
            persona=persona,
            questions=questions,
        )


# Convenience function for quick calls
async def call_user_for_feedback(
    message: str,
    persona_name: str = "C-3PO",
    to_number: Optional[str] = None,
    questions: Optional[list] = None,
) -> Dict:
    """
    Quick feedback call to user.

    Args:
        message: Message to speak
        persona_name: Persona to use (default: C-3PO)
        to_number: Phone number (reads from env/config if not provided)
        questions: Optional list of questions

    Returns:
        Call result dict
    """
    from ..personas.manager import PersonaManager

    # Get recipient phone number
    if not to_number:
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
            return {"success": False, "error": "No phone number configured"}

    # Load persona
    personas_dir = Path(__file__).parent.parent.parent.parent / "personas"
    persona_manager = PersonaManager(personas_dir=personas_dir)
    persona = persona_manager.get_persona(persona_name)

    if not persona:
        return {"success": False, "error": f"Persona {persona_name} not found"}

    # Make call
    caller = OutboundCaller()
    return await caller.make_call(
        to_number=to_number,
        message=message,
        persona=persona,
        questions=questions,
    )
