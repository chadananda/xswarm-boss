"""
Webhook auto-update helpers for Twilio and SendGrid.

Automatically updates external service webhooks when tunnel URLs change.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def update_twilio_webhook(ws_url: str) -> bool:
    """Update Twilio phone number to use new ngrok tunnel URL.

    Args:
        ws_url: WebSocket URL (wss://...) for Twilio Media Streams.

    Returns:
        bool: True if update succeeded, False otherwise.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    phone_sid = os.getenv("TWILIO_PHONE_SID")

    if not all([account_sid, auth_token, phone_sid]):
        return False

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)

        # TwiML that connects to WebSocket Media Streams
        # The Cloudflare Workers endpoint generates TwiML with the dynamic WS URL
        twiml_url = f"https://xswarm-webhooks.workers.dev/voice/connect?ws={ws_url}"

        client.incoming_phone_numbers(phone_sid).update(
            voice_url=twiml_url,
            voice_method="POST"
        )
        return True
    except Exception as e:
        logger.warning(f"Twilio webhook update failed: {e}")
        return False


async def update_sendgrid_webhook(tunnel_url: str) -> bool:
    """Update SendGrid Inbound Parse webhook via API.

    Args:
        tunnel_url: Public HTTPS URL for the tunnel (https://...).

    Returns:
        bool: True if update succeeded, False otherwise.
    """
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        return False

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            # First get existing inbound parse settings
            resp = await client.get(
                "https://api.sendgrid.com/v3/user/webhooks/parse/settings",
                headers={"Authorization": f"Bearer {api_key}"}
            )

            if resp.status_code != 200:
                logger.warning(f"SendGrid API error: {resp.status_code}")
                return False

            settings = resp.json().get("result", [])

            # Update each hostname with new URL
            for setting in settings:
                hostname = setting.get("hostname")
                if hostname:
                    await client.patch(
                        f"https://api.sendgrid.com/v3/user/webhooks/parse/settings/{hostname}",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        json={"url": f"{tunnel_url}/email/inbound"}
                    )

        return True
    except Exception as e:
        logger.warning(f"SendGrid webhook update failed: {e}")
        return False


async def update_twilio_sms_webhook(tunnel_url: str) -> bool:
    """Update Twilio SMS webhook URL.

    Args:
        tunnel_url: Public HTTPS URL for the tunnel.

    Returns:
        bool: True if update succeeded, False otherwise.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    phone_sid = os.getenv("TWILIO_PHONE_SID")

    if not all([account_sid, auth_token, phone_sid]):
        return False

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)

        client.incoming_phone_numbers(phone_sid).update(
            sms_url=f"{tunnel_url}/sms/inbound",
            sms_method="POST"
        )
        return True
    except Exception as e:
        logger.warning(f"Twilio SMS webhook update failed: {e}")
        return False


def get_webhook_status() -> dict:
    """Get current webhook configuration status.

    Returns:
        dict: Status of each webhook type.
    """
    return {
        "twilio_configured": all([
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN"),
            os.getenv("TWILIO_PHONE_SID")
        ]),
        "sendgrid_configured": bool(os.getenv("SENDGRID_API_KEY")),
    }
