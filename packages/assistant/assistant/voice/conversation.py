"""
Conversation Loop - manages the full voice conversation pipeline.
VAD → Audio Capture → STT → AI → TTS → Audio Output
This module orchestrates the complete conversation turn lifecycle.
"""
import asyncio
import numpy as np
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from datetime import datetime
# Core components
from .vad import VoiceActivityDetector
from .audio_io import AudioIO
from .moshi_mlx import MoshiBridge
from ..personas.manager import PersonaManager
from ..memory import MemoryManager
from ..memory.memory_orchestrator import MemoryOrchestrator
@dataclass
class ConversationTurn:
    """Represents one conversation turn with full metadata."""
    user_text: str
    assistant_text: str
    persona_name: str
    timestamp: float
    user_audio: Optional[np.ndarray] = None
    assistant_audio: Optional[np.ndarray] = None
    metadata: Optional[Dict[str, Any]] = None
class AIClient:
    """
    Unified AI client wrapper for Claude/OpenAI.
    Automatically selects provider based on available API keys.
    """
    def __init__(self, config):
        """
        Initialize AI client from config.
        Args:
            config: Config object with API keys
        """
        self.config = config
        self.provider = None
        self.client = None
        self._initialize_client()
    def _initialize_client(self):
        """Initialize client based on available API keys."""
        # Check for Anthropic API key first (preferred)
        if self.config.anthropic_api_key:
            try:
                from anthropic import AsyncAnthropic
                self.client = AsyncAnthropic(api_key=self.config.anthropic_api_key)
                self.provider = "anthropic"
                print("✓ AI Client: Anthropic Claude")
                return
            except ImportError:
                print("⚠️  anthropic SDK not installed, trying OpenAI...")
        # Fallback to OpenAI
        if self.config.openai_api_key:
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.config.openai_api_key)
                self.provider = "openai"
                print("✓ AI Client: OpenAI GPT")
                return
            except ImportError:
                print("⚠️  openai SDK not installed")
        # No API keys available
        raise ValueError(
            "No AI API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env "
            "and run with --debug flag."
        )
    async def chat(self, messages: list, max_tokens: int = 1024) -> str:
        """
        Send chat request to AI provider.
        Args:
            messages: List of message dicts with role/content
            max_tokens: Maximum response length
        Returns:
            str: AI response text
        """
        if self.provider == "anthropic":
            return await self._chat_anthropic(messages, max_tokens)
        elif self.provider == "openai":
            return await self._chat_openai(messages, max_tokens)
        else:
            raise RuntimeError("AI client not initialized")
    async def _chat_anthropic(self, messages: list, max_tokens: int) -> str:
        """Chat using Anthropic Claude API."""
        # Separate system message from conversation messages
        system_msg = None
        conversation = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                conversation.append(msg)
        # Call Anthropic API
        response = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=max_tokens,
            messages=conversation,
            system=system_msg if system_msg else None
        )
        return response.content[0].text
    async def _chat_openai(self, messages: list, max_tokens: int) -> str:
        """Chat using OpenAI GPT API."""
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    def is_available(self) -> bool:
        """Check if AI client is available."""
        return self.client is not None
class ConversationLoop:
    """
    Manages the conversation loop with VAD → STT → AI → TTS → Output.
    This class orchestrates the complete voice conversation pipeline:
    1. Listen for voice activity (VAD)
    2. Capture audio when user speaks
    3. Transcribe with Moshi STT (via generate_response)
    4. Get AI response with persona + memory context
    5. Synthesize response with Moshi TTS
    6. Play audio through speakers
    7. Store conversation turn in memory
    8. Emit callbacks for UI updates
    """
    def __init__(
        self,
        moshi_bridge: MoshiBridge,
        persona_manager: PersonaManager,
        memory_manager: MemoryManager,
        ai_client: AIClient,
        memory_orchestrator: Optional[MemoryOrchestrator] = None,
        user_id: str = "default",
        on_turn_complete: Optional[Callable] = None,
        on_state_change: Optional[Callable] = None
    ):
        """
        Initialize conversation loop.
        Args:
            moshi_bridge: Moshi bridge for STT/TTS
            persona_manager: Persona manager for current persona
            memory_manager: Memory manager for conversation history
            ai_client: AI client for generating responses
            memory_orchestrator: Optional memory orchestrator for AI-filtered retrieval
            user_id: User identifier for memory storage
            on_turn_complete: Callback(turn: ConversationTurn) when turn completes
            on_state_change: Callback(state: str) when state changes
        """
        self.moshi = moshi_bridge
        self.persona = persona_manager
        self.memory = memory_manager
        self.ai = ai_client
        self.memory_orchestrator = memory_orchestrator
        self.user_id = user_id
        self.on_turn_complete = on_turn_complete
        self.on_state_change = on_state_change
        # Audio I/O
        self.audio_io = AudioIO(
            sample_rate=24000,
            frame_size=1920,  # 80ms at 24kHz
            channels=1
        )
        # VAD
        self.vad = VoiceActivityDetector(
            threshold=0.02,
            min_speech_duration=5,  # 5 frames = ~400ms
            min_silence_duration=10  # 10 frames = ~800ms
        )
        # State management
        self.running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._audio_buffer = []
        self._is_listening = False
    async def start(self):
        """
        Start the conversation loop.
        Begins audio I/O and starts listening for voice activity.
        """
        self.running = True
        # Start audio I/O
        self.audio_io.start_input(callback=self._on_audio_frame)
        self.audio_io.start_output()
        # Start conversation loop
        self._loop_task = asyncio.create_task(self._conversation_loop())
        print("🎙️  Conversation loop started")
        self._set_state("listening")
    async def stop(self):
        """
        Stop the conversation loop and clean up resources.
        """
        self.running = False
        # Cancel loop task
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        # Stop audio I/O
        self.audio_io.stop()
        print("🛑 Conversation loop stopped")
        self._set_state("idle")
    async def _conversation_loop(self):
        """
        Main conversation loop.
        Runs continuously while self.running is True.
        """
        while self.running:
            try:
                # Wait for voice activity
                if not self._is_listening:
                    await asyncio.sleep(0.05)  # 50ms polling
                    continue
                # Capture audio segment
                user_audio = await self._capture_speech_segment()
                if user_audio is None or len(user_audio) == 0:
                    continue
                # Process conversation turn
                await self._process_turn(user_audio)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Conversation loop error: {e}")
                await asyncio.sleep(1.0)  # Backoff on error
    def _on_audio_frame(self, audio: np.ndarray):
        """
        Audio input callback from AudioIO.
        Processes each audio frame through VAD.
        Args:
            audio: Audio frame (1920 samples at 24kHz)
        """
        # Process through VAD
        is_speaking = self.vad.process_frame(audio)
        # Store audio if speech detected
        if is_speaking:
            self._audio_buffer.append(audio)
            self._is_listening = True
        else:
            # If was listening and now silence, mark buffer ready
            if self._is_listening and len(self._audio_buffer) > 0:
                self._is_listening = False  # Will be processed by loop
    async def _capture_speech_segment(self) -> Optional[np.ndarray]:
        """
        Capture complete speech segment from buffer.
        Returns:
            Audio segment or None if no speech
        """
        if len(self._audio_buffer) == 0:
            return None
        # Concatenate audio buffer
        segment = np.concatenate(self._audio_buffer)
        self._audio_buffer = []
        # Reset VAD
        self.vad.reset()
        return segment
    async def _process_turn(self, user_audio: np.ndarray):
        """
        Process one complete conversation turn.
        Args:
            user_audio: User's audio input
        """
        self._set_state("thinking")
        # Step 1: Update mic amplitude for visualization
        mic_amplitude = self.moshi.get_amplitude(user_audio)
        self.moshi.update_mic_amplitude(user_audio)  # Update Moshi's internal amplitude state

        # Step 2: Retrieve AI-filtered memories (inner monologue)
        inner_monologue = None
        if self.memory_orchestrator and self.memory_orchestrator.is_available():
            try:
                # Get recent conversation context for query
                recent_context = await self.memory.get_conversation_history(
                    user_id=self.user_id,
                    limit=5
                )

                # Retrieve filtered memories
                # Note: We use a generic query since we don't have transcribed text yet
                filtered_memories = await self.memory_orchestrator.get_memories(
                    user_id=self.user_id,
                    query=recent_context or "conversation context",
                    context=recent_context,
                    thinking_level="light",
                    max_memories=3
                )

                # Format as inner monologue if we have memories
                if filtered_memories:
                    memory_texts = [f"- {mem.text}" for mem in filtered_memories]
                    inner_monologue = (
                        "[Inner thoughts - relevant memories from past conversations]:\n"
                        + "\n".join(memory_texts)
                    )
                    print(f"💭 Injected {len(filtered_memories)} memories as inner monologue")

            except Exception as e:
                print(f"⚠️  Memory retrieval failed: {e}")

        # Step 3: Use Moshi's generate_response for STT+TTS
        # Note: Moshi doesn't separate STT from generation, it's all in generate_response
        # We inject memories as text_prompt to provide context
        moshi_audio, moshi_text = self.moshi.generate_response(
            user_audio=user_audio,
            text_prompt=inner_monologue,  # Inject memories as context
            max_frames=125  # ~10 seconds
        )
        # Step 4: Get AI-enhanced response (optional enhancement)
        # For now, we'll use Moshi's response directly
        # In future, could transcribe user audio separately and use AI for response
        assistant_text = moshi_text if moshi_text else "[No response]"
        # Step 5: Update Moshi amplitude for visualization
        moshi_amplitude = self.moshi.get_amplitude(moshi_audio)
        self.moshi.update_moshi_amplitude(moshi_audio)  # Update Moshi's internal amplitude state
        # Step 6: Play audio response
        self._set_state("speaking")
        if len(moshi_audio) > 0:
            self.audio_io.play_audio(moshi_audio)
            # Wait for audio to finish playing
            duration = len(moshi_audio) / 24000.0  # seconds
            await asyncio.sleep(duration)
        # Step 7: Store conversation turn in memory
        persona_name = self.persona.get_current_persona().name
        await self.memory.store_message(
            user_id=self.user_id,
            message="[Audio input]",  # Placeholder - Moshi doesn't transcribe separately
            role="user",
            metadata={"persona": persona_name}
        )
        await self.memory.store_message(
            user_id=self.user_id,
            message=assistant_text,
            role="assistant",
            metadata={"persona": persona_name}
        )
        # Step 8: Create turn object and invoke callback
        turn = ConversationTurn(
            user_text="[Audio input]",
            assistant_text=assistant_text,
            persona_name=persona_name,
            timestamp=datetime.now().timestamp(),
            user_audio=user_audio,
            assistant_audio=moshi_audio,
            metadata={
                "mic_amplitude": mic_amplitude,
                "moshi_amplitude": moshi_amplitude,
                "inner_monologue": inner_monologue  # Include memories for debugging
            }
        )
        if self.on_turn_complete:
            try:
                self.on_turn_complete(turn)
            except Exception as e:
                print(f"⚠️  Turn complete callback error: {e}")
        # Step 9: Return to listening
        self._set_state("listening")
        self._is_listening = False  # Ready for next speech segment
    def _set_state(self, state: str):
        """
        Set conversation state and invoke callback.
        Args:
            state: New state ("idle", "listening", "thinking", "speaking")
        """
        if self.on_state_change:
            try:
                self.on_state_change(state)
            except Exception as e:
                print(f"⚠️  State change callback error: {e}")
    def get_amplitudes(self) -> Dict[str, float]:
        """
        Get current audio amplitudes for visualization.
        Returns:
            Dict with mic_amplitude and moshi_amplitude
        """
        return {
            "mic_amplitude": self.moshi.mic_amplitude,
            "moshi_amplitude": self.moshi.moshi_amplitude
        }
