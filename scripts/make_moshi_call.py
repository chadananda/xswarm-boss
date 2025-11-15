#!/usr/bin/env python3
"""
Make an outbound call to test Moshi phone integration.

Usage:
    python scripts/make_moshi_call.py --tunnel-url wss://xxx.trycloudflare.com --to +19167656913
"""

import os
import sys
from pathlib import Path
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
import argparse
from dotenv import load_dotenv

# Load environment variables from .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def make_call(tunnel_url: str, to_number: str, from_number: str = None):
    """
    Make an outbound call that connects to Moshi via WebSocket.

    Args:
        tunnel_url: Cloudflare tunnel URL (wss://...)
        to_number: Phone number to call (E.164 format)
        from_number: Twilio number to call from (optional, uses env var)
    """
    # Load Twilio credentials from environment
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        print("❌ Missing Twilio credentials in environment")
        print("   Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
        sys.exit(1)

    # Use provided from_number or get from env
    if not from_number:
        from_number = os.getenv("ADMIN_ASSISTANT_PHONE_NUMBER")

    if not from_number:
        print("❌ Missing from_number (Twilio phone number)")
        print("   Set ADMIN_ASSISTANT_PHONE_NUMBER or pass --from")
        sys.exit(1)

    print("=" * 60)
    print("🎙️  Making Moshi Test Call")
    print("=" * 60)
    print()
    print(f"From: {from_number}")
    print(f"To:   {to_number}")
    print(f"WebSocket: {tunnel_url}")
    print()

    # Create Twilio client
    client = Client(account_sid, auth_token)

    # Create TwiML that connects to Media Streams WebSocket
    # Pass phone numbers as custom parameters
    response = VoiceResponse()
    connect = Connect()
    stream = Stream(url=tunnel_url)
    stream.parameter(name="From", value=from_number)
    stream.parameter(name="To", value=to_number)
    connect.append(stream)
    response.append(connect)

    # Convert TwiML to string
    twiml = str(response)

    print("TwiML:")
    print(twiml)
    print()

    # Make the call
    print("📞 Initiating call...")
    try:
        call = client.calls.create(
            twiml=twiml,
            to=to_number,
            from_=from_number
        )

        print(f"✅ Call initiated!")
        print(f"   Call SID: {call.sid}")
        print(f"   Status: {call.status}")
        print()
        print("The phone should ring shortly...")
        print("When you answer, you'll be connected to Moshi!")
        print()

        return call.sid

    except Exception as e:
        print(f"❌ Error making call: {e}")
        sys.exit(1)


def main():
    """Run the call maker."""
    parser = argparse.ArgumentParser(description="Make a Moshi test call")
    parser.add_argument(
        "--tunnel-url",
        required=True,
        help="Cloudflare tunnel URL (wss://...)"
    )
    parser.add_argument(
        "--to",
        required=True,
        help="Phone number to call (E.164 format, e.g., +19167656913)"
    )
    parser.add_argument(
        "--from",
        dest="from_number",
        help="Twilio number to call from (optional, uses env var)"
    )
    args = parser.parse_args()

    # Make the call
    make_call(
        tunnel_url=args.tunnel_url,
        to_number=args.to,
        from_number=args.from_number
    )


if __name__ == "__main__":
    main()
