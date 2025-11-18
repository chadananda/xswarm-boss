"""
Twilio Voice Bridge - Connects Moshi MLX to phone calls.

Handles bidirectional audio streaming between Twilio Media Streams
and Moshi for natural voice conversations over the phone.
"""

import asyncio
import time
import numpy as np
from typing import Optional, Callable
from pathlib import Path

from ..voice.moshi_pytorch import MoshiBridge
from ..personas.manager import PersonaManager
from ..personas.config import PersonaConfig
from ..memory import MemoryManager
from .audio_converter import mulaw_to_pcm24k, pcm24k_to_mulaw


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
        print(f"[TwilioVoiceBridge] Initializing for call {self.call_sid}")

        # Moshi should be pre-loaded, just create LM generator
        if self.moshi is None:
            raise ValueError("Moshi instance not provided - should be pre-loaded at server startup")

        # Create persistent LM generator for streaming
        self.lm_gen = self.moshi.create_lm_generator(max_steps=500)
        print(f"[TwilioVoiceBridge] LM generator created (using pre-loaded Moshi)")

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
        print(f"[TwilioVoiceBridge] Received {len(pcm_24k)} PCM samples")

        # Add to buffer
        self._input_buffer.append(pcm_24k)
        # Calculate total buffered samples
        total_samples = sum(len(chunk) for chunk in self._input_buffer)
        print(f"[TwilioVoiceBridge] Buffer has {total_samples} samples (need {self._frame_size})")

        # Not enough for a frame yet
        if total_samples < self._frame_size:
            return None

        # Extract exactly one frame (80ms = 1920 samples)
        frame = self._concatenate_buffer(self._frame_size)
        print(f"[TwilioVoiceBridge] Processing frame of {len(frame)} samples")

        # Process frame through Moshi (streaming!)
        response_audio, text_piece = self.moshi.step_frame(self.lm_gen, frame)

        # If Moshi generated audio, convert and return
        if response_audio is not None and len(response_audio) > 0:
            print(f"[TwilioVoiceBridge] Moshi generated {len(response_audio)} samples")
            # Track text for transcript (optional, for logging)
            if text_piece:
                print(f"[TwilioVoiceBridge] Moshi text: '{text_piece}'")
                # Accumulate text (could be used for real-time transcript)
                pass
            # Convert to mulaw and return immediately
            mulaw_response = pcm24k_to_mulaw(response_audio)
            print(f"[TwilioVoiceBridge] Sending {len(mulaw_response)} bytes back to Twilio")
            return mulaw_response
        else:
            print(f"[TwilioVoiceBridge] Moshi returned no audio (still listening)")
        return None

    def _concatenate_buffer(self, num_samples: int) -> np.ndarray:
        """
        Extract and concatenate samples from buffer.

        Args:
            num_samples: Number of samples to extract

        Returns:
            Concatenated audio array
        """
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
        """
        Generate Moshi's initial greeting.

        Returns:
            Base64-encoded mulaw greeting audio
        """
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
        print(f"[TwilioVoiceBridge] Greeting: {greeting_text}")
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
        print(f"[TwilioVoiceBridge] Cleanup for call {self.call_sid}")

        # Save final transcript to memory
        if len(self._call_transcript) > 0:
            user_id = self.from_number.replace("+", "")
            try:
                await self.memory_manager.store_conversation(
                    user_id=user_id,
                    messages=self._call_transcript
                )
            except Exception as e:
                print(f"[TwilioVoiceBridge] Error saving transcript: {e}")

        self._input_buffer = []
        self._call_transcript = []

    def get_transcript(self) -> list:
        """Get conversation transcript for this call."""
        return self._call_transcript.copy()
