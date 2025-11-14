"""
Twilio Media Streams WebSocket Server.

Handles bidirectional audio streaming between Twilio and Moshi
using the Twilio Media Streams protocol.
"""

import asyncio
import json
import websockets
from typing import Dict, Callable, Optional
from datetime import datetime

from .twilio_voice_bridge import TwilioVoiceBridge


class MediaStreamsServer:
    """
    WebSocket server for Twilio Media Streams.

    Manages:
    - WebSocket connections from Twilio
    - Session management (multiple concurrent calls)
    - Message routing (start, media, stop, mark, dtmf)
    - Integration with TwilioVoiceBridge
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 5000,
        bridge_factory: Optional[Callable] = None,
    ):
        """
        Initialize Media Streams server.

        Args:
            host: Server host (default: "0.0.0.0")
            port: Server port (default: 5000)
            bridge_factory: Function to create TwilioVoiceBridge per call
                           Signature: async def factory(call_sid, from_number, to_number) -> TwilioVoiceBridge
        """
        self.host = host
        self.port = port
        self.bridge_factory = bridge_factory

        # Active sessions (call_sid -> bridge)
        self._sessions: Dict[str, TwilioVoiceBridge] = {}

        # Stream metadata (stream_sid -> call_sid)
        self._streams: Dict[str, str] = {}

    async def start(self):
        """Start WebSocket server."""
        print(f"🎙️  Twilio Media Streams server starting on ws://{self.host}:{self.port}")

        async with websockets.serve(self.handle_connection, self.host, self.port):
            print(f"✅ Server ready - waiting for connections...")
            await asyncio.Future()  # Run forever

    async def handle_connection(self, websocket, path):
        """
        Handle incoming Twilio WebSocket connection.

        Args:
            websocket: WebSocket connection
            path: Request path
        """
        stream_sid = None
        call_sid = None
        bridge = None

        print(f"[MediaStreams] New connection from {websocket.remote_address}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    event = data.get("event")

                    if event == "start":
                        # Initialize call session
                        stream_sid, call_sid, bridge = await self._handle_start(data, websocket)

                    elif event == "media":
                        # Process audio chunk
                        if bridge:
                            await self._handle_media(data, bridge, websocket, stream_sid)

                    elif event == "stop":
                        # End call session
                        await self._handle_stop(data, bridge)

                    elif event == "mark":
                        # Audio playback marker (for tracking)
                        pass  # Can use for debugging/monitoring

                    elif event == "dtmf":
                        # DTMF tone (keypad input)
                        # Could use for menu navigation in future
                        pass

                except json.JSONDecodeError:
                    print(f"[MediaStreams] Invalid JSON: {message[:100]}")

        except websockets.exceptions.ConnectionClosed:
            print(f"[MediaStreams] Connection closed for stream {stream_sid}")

        finally:
            # Cleanup on disconnect
            if bridge:
                await bridge.cleanup()

            if call_sid and call_sid in self._sessions:
                del self._sessions[call_sid]

            if stream_sid and stream_sid in self._streams:
                del self._streams[stream_sid]

    async def _handle_start(self, data: dict, websocket) -> tuple:
        """
        Handle 'start' message from Twilio.

        Args:
            data: Start message data
            websocket: WebSocket connection

        Returns:
            (stream_sid, call_sid, bridge)
        """
        start_data = data.get("start", {})
        stream_sid = data.get("streamSid")
        call_sid = start_data.get("callSid")
        from_number = start_data.get("customParameters", {}).get("From") or start_data.get("from")
        to_number = start_data.get("customParameters", {}).get("To") or start_data.get("to")

        print(f"[MediaStreams] Call started: {call_sid}")
        print(f"              From: {from_number}")
        print(f"              To: {to_number}")
        print(f"              Stream: {stream_sid}")

        # Create bridge for this call
        if self.bridge_factory:
            bridge = await self.bridge_factory(call_sid, from_number, to_number)
            await bridge.initialize()
        else:
            raise ValueError("No bridge factory configured")

        # Store session
        self._sessions[call_sid] = bridge
        self._streams[stream_sid] = call_sid

        return stream_sid, call_sid, bridge

    async def _handle_media(self, data: dict, bridge: TwilioVoiceBridge, websocket, stream_sid: str):
        """
        Handle 'media' message from Twilio.

        Args:
            data: Media message data
            bridge: TwilioVoiceBridge for this call
            websocket: WebSocket connection
            stream_sid: Stream SID
        """
        media_data = data.get("media", {})
        payload = media_data.get("payload")  # Base64 mulaw audio

        if not payload:
            return

        # Send audio to bridge for processing
        response_payload = await bridge.process_audio_chunk(payload)

        # If bridge has a response, send it back
        if response_payload:
            await self.send_audio(websocket, stream_sid, response_payload)

    async def _handle_stop(self, data: dict, bridge: Optional[TwilioVoiceBridge]):
        """
        Handle 'stop' message from Twilio.

        Args:
            data: Stop message data
            bridge: TwilioVoiceBridge for this call (if exists)
        """
        stop_data = data.get("stop", {})
        call_sid = stop_data.get("callSid")

        print(f"[MediaStreams] Call ended: {call_sid}")

        if bridge:
            transcript = bridge.get_transcript()
            print(f"[MediaStreams] Transcript: {len(transcript)} messages")

    async def send_audio(self, websocket, stream_sid: str, audio_payload: str):
        """
        Send audio back to Twilio.

        Args:
            websocket: WebSocket connection
            stream_sid: Stream SID
            audio_payload: Base64-encoded mulaw audio
        """
        message = {
            "event": "media",
            "streamSid": stream_sid,
            "media": {
                "payload": audio_payload
            }
        }

        try:
            await websocket.send(json.dumps(message))
        except Exception as e:
            print(f"[MediaStreams] Error sending audio: {e}")

    async def send_mark(self, websocket, stream_sid: str, name: str):
        """
        Send mark event to Twilio (for playback tracking).

        Args:
            websocket: WebSocket connection
            stream_sid: Stream SID
            name: Mark name
        """
        message = {
            "event": "mark",
            "streamSid": stream_sid,
            "mark": {
                "name": name
            }
        }

        try:
            await websocket.send(json.dumps(message))
        except Exception as e:
            print(f"[MediaStreams] Error sending mark: {e}")

    def get_active_calls(self) -> list:
        """Get list of active call SIDs."""
        return list(self._sessions.keys())

    def get_call_info(self, call_sid: str) -> Optional[dict]:
        """
        Get information about a specific call.

        Args:
            call_sid: Call SID

        Returns:
            Dict with call info (state, transcript, etc.)
        """
        bridge = self._sessions.get(call_sid)
        if not bridge:
            return None

        return {
            "call_sid": call_sid,
            "from_number": bridge.from_number,
            "to_number": bridge.to_number,
            "state": bridge.state,
            "transcript": bridge.get_transcript(),
        }
