"""
Phone Module.
Consolidates OutboundCaller, TwilioVoiceBridge, MediaStreamsServer, and audio conversion logic.
"""

import os
import asyncio
import json
import time
import base64
import audioop
import logging
import websockets
import numpy as np
from scipy import signal
from typing import Dict, Optional, List, Callable
from pathlib import Path
from datetime import datetime
import toml
from twilio.rest import Client

logger = logging.getLogger(__name__)
from .personas.config import PersonaConfig
from .personas.manager import PersonaManager
from .memory import MemoryManager
from .voice import MoshiBridge

# ==============================================================================
# AUDIO CONVERTER
# ==============================================================================

def mulaw_to_pcm24k(mulaw_8k_base64: str) -> np.ndarray:
    """
    Convert Twilio mulaw audio to Moshi PCM format.

    Pipeline:
    1. base64 decode → mulaw 8kHz bytes
    2. mulaw decode → PCM 8kHz int16
    3. resample → PCM 24kHz int16
    4. normalize → PCM 24kHz float32 [-1.0, 1.0]
    """
    # Step 1: Decode base64 to mulaw bytes
    mulaw_bytes = base64.b64decode(mulaw_8k_base64)

    # Handle empty audio
    if len(mulaw_bytes) == 0:
        return np.array([], dtype=np.float32)

    # Step 2: Decode mulaw to PCM 8kHz int16
    # audioop.ulaw2lin converts mulaw to linear PCM
    # width=2 means 16-bit (int16)
    pcm_8k_bytes = audioop.ulaw2lin(mulaw_bytes, 2)

    # Convert bytes to numpy array
    pcm_8k_int16 = np.frombuffer(pcm_8k_bytes, dtype=np.int16)

    # Step 3: Resample from 8kHz to 24kHz (3x upsampling)
    # scipy.signal.resample uses FFT for high-quality resampling
    num_samples_24k = len(pcm_8k_int16) * 3
    pcm_24k_int16 = signal.resample(pcm_8k_int16, num_samples_24k).astype(np.int16)

    # Step 4: Normalize to float32 [-1.0, 1.0]
    pcm_24k_float32 = pcm_24k_int16.astype(np.float32) / 32768.0

    return pcm_24k_float32


def pcm24k_to_mulaw(pcm_24k_float32: np.ndarray) -> str:
    """
    Convert Moshi PCM audio to Twilio mulaw format.

    Pipeline:
    1. denormalize → PCM 24kHz int16
    2. resample → PCM 8kHz int16
    3. mulaw encode → mulaw 8kHz bytes
    4. base64 encode → mulaw 8kHz base64
    """
    # Step 1: Denormalize from float32 [-1.0, 1.0] to int16
    pcm_24k_int16 = (pcm_24k_float32 * 32767.0).astype(np.int16)

    # Step 2: Resample from 24kHz to 8kHz (3x downsampling)
    num_samples_8k = len(pcm_24k_int16) // 3
    pcm_8k_int16 = signal.resample(pcm_24k_int16, num_samples_8k).astype(np.int16)

    # Step 3: Encode PCM to mulaw
    # audioop.lin2ulaw converts linear PCM to mulaw
    # width=2 means 16-bit input
    pcm_8k_bytes = pcm_8k_int16.tobytes()
    mulaw_bytes = audioop.lin2ulaw(pcm_8k_bytes, 2)

    # Step 4: Encode to base64
    mulaw_base64 = base64.b64encode(mulaw_bytes).decode('utf-8')

    return mulaw_base64


def get_audio_stats(audio: np.ndarray) -> dict:
    """Get audio statistics for debugging."""
    return {
        "min": float(np.min(audio)),
        "max": float(np.max(audio)),
        "mean": float(np.mean(audio)),
        "rms": float(np.sqrt(np.mean(audio ** 2))),
        "samples": len(audio),
    }


# ==============================================================================
# OUTBOUND CALLER
# ==============================================================================

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
            # Log warning instead of raising error to allow app to start without Twilio
            logger.warning("Twilio credentials not found. Phone functionality disabled.")
            self.client = None
            return

        if not self.from_number:
             logger.warning("Twilio phone number not found. Phone functionality disabled.")
             self.client = None
             return

        # Initialize Twilio client
        self.client = Client(self.account_sid, self.auth_token)

    def _generate_twiml_for_persona(
        self,
        persona: PersonaConfig,
        message: str,
        questions: Optional[list] = None,
    ) -> str:
        """Generate TwiML for persona-specific voice call."""
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
        """Make an outbound call with persona voice."""
        if not self.client:
            return {"success": False, "error": "Twilio client not initialized"}

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
        """Make a feedback call for development status."""
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
    """Quick feedback call to user."""
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


# ==============================================================================
# TWILIO VOICE BRIDGE
# ==============================================================================

class TwilioVoiceBridge:
    """
    Phone call voice bridge using Moshi MLX.

    Manages:
    - Audio buffering and frame detection
    - Moshi STT → AI → TTS pipeline
    - Persona and memory integration
    - Conversation state tracking
    """

    def __init__(
        self,
        call_sid: str,
        from_number: str,
        to_number: str,
        persona_manager: PersonaManager,
        memory_manager: MemoryManager,
        config,
        moshi: Optional[MoshiBridge] = None,
        on_state_change: Optional[Callable] = None,
    ):
        """
        Initialize Twilio voice bridge.

        Args:
            call_sid: Twilio call SID (unique identifier)
            from_number: Caller's phone number
            to_number: Recipient's phone number
            persona_manager: Persona manager
            memory_manager: Memory manager
            config: Config with API keys
            moshi: Pre-loaded MoshiBridge instance (if None, will be loaded)
            on_state_change: Optional callback for state changes
        """
        self.call_sid = call_sid
        self.from_number = from_number
        self.to_number = to_number
        self.persona_manager = persona_manager
        self.memory_manager = memory_manager
        self.config = config

        # Moshi bridge (pre-loaded or will be loaded)
        self.moshi: Optional[MoshiBridge] = moshi
        self.lm_gen = None  # Persistent LM generator for streaming
        self._greeting_sent = False  # Track if greeting was sent

        # Audio buffering (for frame accumulation only)
        self._input_buffer = []  # Accumulate incoming audio chunks
        self._frame_size = 1920  # 80ms at 24kHz (Moshi frame size)

        # State tracking
        self.state = "idle"  # idle, listening, thinking, speaking
        self._on_state_change = on_state_change or (lambda s: None)

        # Conversation history (for this call)
        self._call_transcript = []

    async def initialize(self):
        """Initialize bridge (Moshi should already be pre-loaded)."""
        logger.debug(f"[TwilioVoiceBridge] Initializing for call {self.call_sid}")

        # Moshi should be pre-loaded, just create LM generator
        if self.moshi is None:
            raise ValueError("Moshi instance not provided - should be pre-loaded at server startup")

        # Create persistent LM generator for streaming
        self.lm_gen = self.moshi.create_lm_generator(max_steps=500)
        logger.debug(f"[TwilioVoiceBridge] LM generator created (using pre-loaded Moshi)")

        # Initialize memory for this user (use phone number as user_id)
        user_id = self.from_number.replace("+", "")
        await self.memory_manager.initialize()

        self._set_state("listening")

    async def process_audio_chunk(self, mulaw_base64: str) -> Optional[str]:
        """
        Process incoming audio chunk in streaming mode.

        Args:
            mulaw_base64: Base64-encoded mulaw 8kHz audio from Twilio

        Returns:
            Base64-encoded mulaw 8kHz response audio (if any), else None
        """
        # Convert Twilio audio to Moshi format
        pcm_24k = mulaw_to_pcm24k(mulaw_base64)
        logger.debug(f"[TwilioVoiceBridge] Received {len(pcm_24k)} PCM samples")

        # Add to buffer
        self._input_buffer.append(pcm_24k)
        # Calculate total buffered samples
        total_samples = sum(len(chunk) for chunk in self._input_buffer)
        logger.debug(f"[TwilioVoiceBridge] Buffer has {total_samples} samples (need {self._frame_size})")

        # Not enough for a frame yet
        if total_samples < self._frame_size:
            return None

        # Extract exactly one frame (80ms = 1920 samples)
        frame = self._concatenate_buffer(self._frame_size)
        logger.debug(f"[TwilioVoiceBridge] Processing frame of {len(frame)} samples")

        # Process frame through Moshi (streaming!)
        response_audio, text_piece = self.moshi.step_frame(self.lm_gen, frame)

        # If Moshi generated audio, convert and return
        if response_audio is not None and len(response_audio) > 0:
            logger.debug(f"[TwilioVoiceBridge] Moshi generated {len(response_audio)} samples")
            # Track text for transcript (optional, for logging)
            if text_piece:
                logger.debug(f"[TwilioVoiceBridge] Moshi text: '{text_piece}'")
                # Accumulate text (could be used for real-time transcript)
                pass
            # Convert to mulaw and return immediately
            mulaw_response = pcm24k_to_mulaw(response_audio)
            logger.debug(f"[TwilioVoiceBridge] Sending {len(mulaw_response)} bytes back to Twilio")
            return mulaw_response
        else:
            logger.debug(f"[TwilioVoiceBridge] Moshi returned no audio (still listening)")
        return None

    def _concatenate_buffer(self, num_samples: int) -> np.ndarray:
        """Extract and concatenate samples from buffer."""
        result = []
        remaining = num_samples

        while remaining > 0 and len(self._input_buffer) > 0:
            chunk = self._input_buffer[0]

            if len(chunk) <= remaining:
                # Take entire chunk
                result.append(chunk)
                remaining -= len(chunk)
                self._input_buffer.pop(0)
            else:
                # Take partial chunk
                result.append(chunk[:remaining])
                self._input_buffer[0] = chunk[remaining:]
                remaining = 0

        return np.concatenate(result) if result else np.array([], dtype=np.float32)

    async def generate_and_send_greeting(self) -> str:
        """Generate Moshi's initial greeting."""
        if self._greeting_sent:
            return ""
        self._greeting_sent = True
        # Get current persona
        persona = self.persona_manager.get_current_persona()
        if not persona:
            persona = self.persona_manager.get_persona("C-3PO")
        # Build greeting prompt
        persona_prompt = persona.system_prompt or f"You are {persona.name}."
        persona_prompt += "\n\nYou just answered a phone call. Introduce yourself briefly and ask how you can help."
        # Generate greeting
        self._set_state("speaking")
        greeting_audio, greeting_text = self.moshi.generate_greeting(
            self.lm_gen,
            persona_prompt=persona_prompt,
            num_frames=25  # ~2 seconds
        )
        # Log greeting
        logger.debug(f"[TwilioVoiceBridge] Greeting: {greeting_text}")
        # Store in transcript
        self._call_transcript.append({
            "role": "assistant",
            "content": greeting_text or "[Greeting audio]",
            "timestamp": time.time(),
        })
        self._set_state("listening")
        # Convert to mulaw
        mulaw_greeting = pcm24k_to_mulaw(greeting_audio)
        return mulaw_greeting

    def _set_state(self, new_state: str):
        """Update state and notify callback."""
        if new_state != self.state:
            self.state = new_state
            self._on_state_change(new_state)

    async def cleanup(self):
        """Cleanup resources when call ends."""
        logger.debug(f"[TwilioVoiceBridge] Cleanup for call {self.call_sid}")

        # Save final transcript to memory
        if len(self._call_transcript) > 0:
            user_id = self.from_number.replace("+", "")
            try:
                await self.memory_manager.store_conversation(
                    user_id=user_id,
                    messages=self._call_transcript
                )
            except Exception as e:
                logger.error(f"[TwilioVoiceBridge] Error saving transcript: {e}")

        self._input_buffer = []
        self._call_transcript = []

    def get_transcript(self) -> list:
        """Get conversation transcript for this call."""
        return self._call_transcript.copy()


# ==============================================================================
# MEDIA STREAMS SERVER
# ==============================================================================

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
        logger.info(f"Twilio Media Streams server starting on ws://{self.host}:{self.port}")

        async with websockets.serve(self.handle_connection, self.host, self.port):
            logger.info(f"Server ready - waiting for connections...")
            await asyncio.Future()  # Run forever

    async def handle_connection(self, websocket):
        """Handle incoming Twilio WebSocket connection."""
        stream_sid = None
        call_sid = None
        bridge = None

        logger.debug(f"[MediaStreams] New connection from {websocket.remote_address}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    event = data.get("event")

                    if event == "start":
                        # Initialize call session
                        stream_sid, call_sid, bridge = await self._handle_start(data, websocket)
                        # Send greeting to test audio playback
                        logger.debug("[MediaStreams] Generating greeting...")
                        greeting_audio = await bridge.generate_and_send_greeting()
                        if greeting_audio:
                            logger.debug(f"[MediaStreams] Sending greeting audio ({len(greeting_audio)} bytes)")
                            await self.send_audio(websocket, stream_sid, greeting_audio)
                        else:
                            logger.debug("[MediaStreams] No greeting audio generated")

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
                    logger.warning(f"[MediaStreams] Invalid JSON: {message[:100]}")

        except websockets.exceptions.ConnectionClosed:
            logger.debug(f"[MediaStreams] Connection closed for stream {stream_sid}")

        finally:
            # Cleanup on disconnect
            if bridge:
                await bridge.cleanup()

            if call_sid and call_sid in self._sessions:
                del self._sessions[call_sid]

            if stream_sid and stream_sid in self._streams:
                del self._streams[stream_sid]

    async def _handle_start(self, data: dict, websocket) -> tuple:
        """Handle 'start' message from Twilio."""
        start_data = data.get("start", {})
        stream_sid = data.get("streamSid")
        call_sid = start_data.get("callSid")
        from_number = start_data.get("customParameters", {}).get("From") or start_data.get("from")
        to_number = start_data.get("customParameters", {}).get("To") or start_data.get("to")

        logger.info(f"[MediaStreams] Call started: {call_sid}")
        logger.debug(f"              From: {from_number}")
        logger.debug(f"              To: {to_number}")
        logger.debug(f"              Stream: {stream_sid}")

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
        """Handle 'media' message from Twilio."""
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
        """Handle 'stop' message from Twilio."""
        stop_data = data.get("stop", {})
        call_sid = stop_data.get("callSid")

        logger.info(f"[MediaStreams] Call ended: {call_sid}")

        if bridge:
            transcript = bridge.get_transcript()
            logger.debug(f"[MediaStreams] Transcript: {len(transcript)} messages")

    async def send_audio(self, websocket, stream_sid: str, audio_payload: str):
        """Send audio back to Twilio."""
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
            logger.error(f"[MediaStreams] Error sending audio: {e}")

    async def send_mark(self, websocket, stream_sid: str, name: str):
        """Send mark event to Twilio (for playback tracking)."""
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
            logger.error(f"[MediaStreams] Error sending mark: {e}")

    def get_active_calls(self) -> list:
        """Get list of active call SIDs."""
        return list(self._sessions.keys())

    def get_call_info(self, call_sid: str) -> Optional[dict]:
        """Get information about a specific call."""
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
