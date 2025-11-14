"""
Twilio Voice Bridge - Connects Moshi MLX to phone calls.

Handles bidirectional audio streaming between Twilio Media Streams
and Moshi for natural voice conversations over the phone.
"""

import asyncio
import numpy as np
from typing import Optional, Callable
from pathlib import Path

from ..voice.moshi_mlx import MoshiBridge
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
        moshi_quality: str = "auto",
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
            moshi_quality: "auto", "bf16", "q8", "q4"
            on_state_change: Optional callback for state changes
        """
        self.call_sid = call_sid
        self.from_number = from_number
        self.to_number = to_number
        self.persona_manager = persona_manager
        self.memory_manager = memory_manager
        self.config = config
        self.moshi_quality = moshi_quality

        # Moshi bridge (lazy loaded)
        self.moshi: Optional[MoshiBridge] = None

        # Audio buffering
        self._input_buffer = []  # Accumulate incoming audio chunks
        self._frame_size = 1920  # 80ms at 24kHz (Moshi frame size)
        self._silence_threshold = 0.02  # RMS threshold for silence detection
        self._speech_timeout_frames = 15  # ~1.2 seconds of silence ends turn

        # State tracking
        self.state = "idle"  # idle, listening, thinking, speaking
        self._silence_frames = 0
        self._on_state_change = on_state_change or (lambda s: None)

        # Conversation history (for this call)
        self._call_transcript = []

    async def initialize(self):
        """Initialize Moshi models and AI client."""
        print(f"[TwilioVoiceBridge] Initializing for call {self.call_sid}")

        # Initialize Moshi
        from ..voice.moshi_mlx import MoshiBridge

        # Determine quality setting
        if self.moshi_quality == "auto":
            # Use q8 for phone calls (balanced quality/performance)
            quality = "q8"
        else:
            quality = self.moshi_quality

        self.moshi = MoshiBridge(
            hf_repo=f"kyutai/moshiko-mlx-{quality}",
            quantized=int(quality[1]) if quality.startswith("q") else None,
            max_steps=500
        )

        print(f"[TwilioVoiceBridge] Moshi loaded ({quality})")

        # Initialize memory for this user (use phone number as user_id)
        user_id = self.from_number.replace("+", "")
        await self.memory_manager.initialize()

        self._set_state("listening")

    async def process_audio_chunk(self, mulaw_base64: str) -> Optional[str]:
        """
        Process incoming audio chunk from phone.

        Args:
            mulaw_base64: Base64-encoded mulaw 8kHz audio from Twilio

        Returns:
            Base64-encoded mulaw 8kHz response audio (if ready), else None
        """
        # Convert Twilio audio to Moshi format
        pcm_24k = mulaw_to_pcm24k(mulaw_base64)

        # Add to buffer
        self._input_buffer.append(pcm_24k)

        # Calculate total buffered samples
        total_samples = sum(len(chunk) for chunk in self._input_buffer)

        # Check if we have enough for a full frame (80ms = 1920 samples at 24kHz)
        if total_samples < self._frame_size:
            return None

        # Extract a frame
        frame = self._concatenate_buffer(self._frame_size)

        # Check for silence (end of speech)
        rms = np.sqrt(np.mean(frame ** 2))

        if rms < self._silence_threshold:
            self._silence_frames += 1

            # If enough silence, process accumulated speech
            if self._silence_frames >= self._speech_timeout_frames:
                if len(self._input_buffer) > 0:
                    # We have accumulated speech - process it
                    return await self._process_speech()
                else:
                    # Just silence, keep listening
                    self._silence_frames = 0
                    return None
        else:
            # Speech detected - reset silence counter
            self._silence_frames = 0

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

    async def _process_speech(self) -> str:
        """
        Process accumulated speech and generate response.

        Returns:
            Base64-encoded mulaw response audio
        """
        self._set_state("thinking")

        # Get all accumulated audio
        user_audio = np.concatenate(self._input_buffer) if self._input_buffer else np.array([], dtype=np.float32)
        self._input_buffer = []
        self._silence_frames = 0

        # Get current persona
        persona = self.persona_manager.get_current_persona()
        if not persona:
            persona = self.persona_manager.get_persona("C-3PO")  # Fallback

        # Build conversation prompt
        text_prompt = await self._build_prompt(persona, user_audio)

        # Generate Moshi response
        self._set_state("speaking")

        try:
            response_audio, response_text = self.moshi.generate_response(
                user_audio,
                text_prompt=text_prompt,
                max_tokens=300  # Keep responses concise for phone
            )

            # Store in conversation history
            self._call_transcript.append({
                "role": "user",
                "content": "[Speech audio]",
                "timestamp": asyncio.get_event_loop().time(),
            })

            self._call_transcript.append({
                "role": "assistant",
                "content": response_text or "[Audio response]",
                "timestamp": asyncio.get_event_loop().time(),
            })

            # Save to memory (async, don't wait)
            user_id = self.from_number.replace("+", "")
            asyncio.create_task(self.memory_manager.store_conversation(
                user_id=user_id,
                messages=self._call_transcript[-2:]  # Last 2 messages
            ))

            # Convert response to Twilio format
            mulaw_response = pcm24k_to_mulaw(response_audio)

            self._set_state("listening")

            return mulaw_response

        except Exception as e:
            print(f"[TwilioVoiceBridge] Error generating response: {e}")
            self._set_state("listening")
            return None

    async def _build_prompt(self, persona: PersonaConfig, user_audio: np.ndarray) -> str:
        """
        Build conversation prompt with persona and context.

        Args:
            persona: Current persona
            user_audio: User's audio (for context)

        Returns:
            Text prompt for Moshi
        """
        # Start with persona system prompt
        prompt = persona.system_prompt or f"You are {persona.name}, a helpful AI assistant."

        # Add phone call context
        prompt += "\n\nYou are currently on a phone call. Keep responses brief and conversational."

        # Add recent conversation history
        if len(self._call_transcript) > 0:
            prompt += "\n\nRecent conversation:"
            for msg in self._call_transcript[-6:]:  # Last 6 messages
                role = "User" if msg["role"] == "user" else persona.name
                content = msg.get("content", "[Audio]")
                prompt += f"\n{role}: {content}"

        return prompt

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
