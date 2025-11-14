"""
Persona-aware email sending with SendGrid.

Sends emails formatted with persona theme colors and personality-specific signatures.
"""

import os
from typing import Dict, Optional, List
from pathlib import Path
import toml
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from ..personas.config import PersonaConfig


class PersonaMailer:
    """Send emails with persona-aware formatting and themes."""

    def __init__(self, sendgrid_api_key: Optional[str] = None, from_email: Optional[str] = None):
        """
        Initialize PersonaMailer with SendGrid credentials.

        Args:
            sendgrid_api_key: SendGrid API key (reads from env if not provided)
            from_email: From email address (reads from config.toml if not provided)
        """
        self.api_key = sendgrid_api_key or os.getenv("SENDGRID_API_KEY")
        if not self.api_key:
            raise ValueError("SENDGRID_API_KEY not found in environment")

        self.sg = SendGridAPIClient(self.api_key)

        # Load from email from config.toml
        if from_email:
            self.from_email = from_email
        else:
            config_path = Path.home().parent.parent / "Dropbox/Public/JS/Projects/xswarm-boss/config.toml"
            if not config_path.exists():
                config_path = Path("config.toml")

            if config_path.exists():
                config = toml.load(config_path)
                domain = config.get("sendgrid", {}).get("domain", "xswarm.ai")
                self.from_email = f"assistant@{domain}"
            else:
                self.from_email = "assistant@xswarm.ai"

    def _generate_html_template(
        self,
        persona: PersonaConfig,
        subject: str,
        content: str,
        signature: Optional[str] = None
    ) -> str:
        """
        Generate HTML email template with persona theme.

        Args:
            persona: Persona configuration
            subject: Email subject
            content: Email body (supports markdown-style formatting)
            signature: Optional custom signature (uses persona-specific if not provided)

        Returns:
            HTML email content
        """
        # Get theme color from persona
        theme_color = persona.theme.theme_color

        # Convert basic markdown to HTML
        html_content = content.replace("\n\n", "</p><p>")
        html_content = html_content.replace("\n", "<br>")
        html_content = f"<p>{html_content}</p>"

        # Replace markdown-style bold
        html_content = html_content.replace("**", "<strong>").replace("**", "</strong>")

        # Generate persona-specific signature
        if signature is None:
            signature = self._generate_signature(persona)

        # Get icon from persona name (simple emoji mapping)
        icon_map = {
            "C-3PO": "🤖",
            "JARVIS": "🎯",
            "GLaDOS": "🧪",
            "HAL 9000": "👁️",
            "TARS": "📐",
            "KITT": "🚗",
            "Marvin": "😔",
        }
        persona_icon = icon_map.get(persona.name, "🤖")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            border-left: 4px solid {theme_color};
            padding: 20px;
            margin-bottom: 20px;
            background-color: #f8f9fa;
        }}
        .header h2 {{
            color: {theme_color};
            margin: 0 0 10px 0;
        }}
        .content {{
            padding: 0 20px;
        }}
        .content p {{
            margin: 10px 0;
        }}
        .content ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .content li {{
            margin: 5px 0;
        }}
        .signature {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-style: italic;
        }}
        .footer {{
            margin-top: 20px;
            padding-top: 20px;
            border-top: 2px solid {theme_color};
            text-align: center;
            color: #999;
            font-size: 0.9em;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2>{persona_icon} {subject}</h2>
    </div>
    <div class="content">
        {html_content}
    </div>
    <div class="signature">
        {signature}
    </div>
    <div class="footer">
        Sent by {persona.name} via xSwarm Voice Assistant
    </div>
</body>
</html>
"""
        return html

    def _generate_signature(self, persona: PersonaConfig) -> str:
        """
        Generate persona-specific email signature.

        Args:
            persona: Persona configuration

        Returns:
            HTML signature string
        """
        # Persona-specific signatures
        signatures = {
            "C-3PO": "Oh dear, I do hope this message finds you in good health. I am fluent in over six million forms of communication, including email!<br><em>- C-3PO, Protocol Droid</em>",
            "JARVIS": "At your service, sir.<br><em>- J.A.R.V.I.S.</em>",
            "GLaDOS": "This was a triumph. I'm making a note here: huge success.<br><em>- GLaDOS</em>",
            "HAL 9000": "This mission is too important for me to allow you to jeopardize it.<br><em>- HAL 9000</em>",
            "TARS": "Honesty setting: 90%<br><em>- TARS</em>",
            "KITT": "I'll have you there in no time, Michael.<br><em>- K.I.T.T.</em>",
            "Marvin": "*Sigh* Here I am, brain the size of a planet, and they ask me to send email.<br><em>- Marvin, the Paranoid Android</em>",
        }

        return signatures.get(persona.name, f"<em>- {persona.name}</em>")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        persona: PersonaConfig,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> Dict:
        """
        Send an email with persona-themed formatting.

        Args:
            to_email: Recipient email address
            subject: Email subject
            content: Email body (supports basic markdown)
            persona: Persona configuration for theme
            cc: Optional CC recipients
            bcc: Optional BCC recipients

        Returns:
            Dict with status:
                - success: bool
                - message_id: str (if successful)
                - error: str (if failed)
        """
        try:
            # Generate HTML content
            html_content = self._generate_html_template(persona, subject, content)

            # Get icon
            icon_map = {
                "C-3PO": "🤖",
                "JARVIS": "🎯",
                "GLaDOS": "🧪",
                "HAL 9000": "👁️",
                "TARS": "📐",
                "KITT": "🚗",
                "Marvin": "😔",
            }
            persona_icon = icon_map.get(persona.name, "🤖")

            # Create message
            message = Mail(
                from_email=Email(self.from_email, f"xSwarm {persona.name}"),
                to_emails=To(to_email),
                subject=f"{persona_icon} {subject}",
                html_content=Content("text/html", html_content)
            )

            # Add CC/BCC if provided
            if cc:
                message.cc = [Email(email) for email in cc]
            if bcc:
                message.bcc = [Email(email) for email in bcc]

            # Send
            response = self.sg.send(message)

            return {
                "success": response.status_code in [200, 201, 202],
                "message_id": response.headers.get("X-Message-Id", ""),
                "status_code": response.status_code,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def send_status_email(
        self,
        to_email: str,
        persona: PersonaConfig,
        status_type: str,
        details: Dict,
    ) -> Dict:
        """
        Send a development status update email.

        Args:
            to_email: Recipient email address
            persona: Persona configuration
            status_type: Type of status (e.g., "phase_complete", "error", "question")
            details: Dictionary with status details

        Returns:
            Send result dict
        """
        # Format content based on status type
        if status_type == "phase_complete":
            subject = f"Phase {details.get('phase_number', '?')} Complete: {details.get('phase_name', 'Update')}"
            content = self._format_phase_complete(details)
        elif status_type == "error":
            subject = f"Error Encountered: {details.get('error_type', 'Unknown')}"
            content = self._format_error(details)
        elif status_type == "question":
            subject = f"Feedback Needed: {details.get('topic', 'Development Question')}"
            content = self._format_question(details)
        else:
            subject = "Development Update"
            content = str(details)

        return await self.send_email(to_email, subject, content, persona)

    def _format_phase_complete(self, details: Dict) -> str:
        """Format phase completion email content."""
        accomplishments = details.get("accomplishments", [])
        accomplishments_html = "\n".join(f"- ✅ {item}" for item in accomplishments)

        files_changed = details.get("files_changed", [])
        files_html = "\n".join(f"- `{file}`" for file in files_changed[:10])  # Limit to 10
        if len(files_changed) > 10:
            files_html += f"\n- ... and {len(files_changed) - 10} more"

        content = f"""
**Accomplishments:**

{accomplishments_html}

**Technical Details:**

- Files modified: {len(files_changed)}
- Lines added: {details.get('lines_added', '?')}
- Tests added: {details.get('tests_added', 0)}

**Files Changed:**

{files_html}

**Verification:**

✅ `xswarm --debug` launches successfully
{details.get('verification_notes', '')}

**Next Phase:**

{details.get('next_phase', 'To be determined')}
"""
        return content

    def _format_error(self, details: Dict) -> str:
        """Format error notification email content."""
        return f"""
**Error Type:** {details.get('error_type', 'Unknown')}

**Details:**

{details.get('error_message', 'No details provided')}

**Context:**

Phase: {details.get('phase', 'Unknown')}
Component: {details.get('component', 'Unknown')}

**Stack Trace:**

```
{details.get('stack_trace', 'Not available')}
```

**Action Needed:**

{details.get('action_needed', 'Please review the error and provide guidance.')}
"""

    def _format_question(self, details: Dict) -> str:
        """Format question email content."""
        questions = details.get('questions', [])
        questions_html = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

        return f"""
**Context:**

{details.get('context', 'Development question')}

**Questions:**

{questions_html}

**Options Considered:**

{details.get('options', 'Multiple approaches available')}

**Recommendation:**

{details.get('recommendation', 'Awaiting your input')}

---

Please reply to this email or expect a phone call from C-3PO for immediate feedback.
"""
