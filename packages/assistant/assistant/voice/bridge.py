"""
Voice Bridge Orchestrator - manages Moshi voice conversation lifecycle.

This orchestration layer coordinates:
- MoshiBridge (voice I/O)
- PersonaManager (personality/voice settings)
- MemoryManager (conversation history)
- State management (IDLE → LISTENING → THINKING → SPEAKING)
"""
import asyncio
import numpy as np
from enum import Enum
from typing import Optional, AsyncGenerator, Dict, Any
from pathlib import Path
# Import core dependencies
from .moshi_mlx import MoshiBridge
from .conversation import ConversationLoop, AIClient, ConversationTurn
from ..personas.manager import PersonaManager
from ..personas.config import PersonaConfig
from ..memory import MemoryManager
class ConversationState(Enum):
    """Conversation states for TUI visualization"""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"
class VoiceBridgeOrchestrator:
    """
    Orchestrates voice conversation using MoshiBridge, PersonaManager, and MemoryManager.

    Manages the complete voice interaction lifecycle:
    1. Initialize Moshi models with persona voice settings
    2. Listen to user audio input (LISTENING state)
    3. Process with Moshi (THINKING state)
    4. Synthesize response (SPEAKING state)
    5. Store conversation in memory
    6. Emit audio stream for visualization
    """
    def __init__(
        self,
        persona_manager: PersonaManager,
        memory_manager: MemoryManager,
        config,
        user_id: str = "default",
        moshi_quality: str = "auto"
    ):
        """
        Initialize voice bridge orchestrator.

        Args:
            persona_manager: Persona manager for current persona settings
            memory_manager: Memory manager for conversation history
            config: Config object with API keys for AI client
            user_id: User identifier for memory storage
            moshi_quality: Moshi quality preset ("auto", "bf16", "q8", "q4")
        """
        self.persona_manager = persona_manager
        self.memory_manager = memory_manager
        self.config = config
        self.user_id = user_id
        self.moshi_quality = moshi_quality
        # Core components (initialized later)
        self.moshi: Optional[MoshiBridge] = None
        self.current_persona: Optional[PersonaConfig] = None
        self.ai_client: Optional[AIClient] = None
        self.conversation_loop: Optional[ConversationLoop] = None
        # State management
        self.state = ConversationState.IDLE
        self.state_callbacks: list = []
        # Audio streaming for visualization
        self._audio_buffer: list[np.ndarray] = []
        self._current_mic_amplitude: float = 0.0
        self._current_moshi_amplitude: float = 0.0
        # Conversation control
        self._running = False
        self._listening_task: Optional[asyncio.Task] = None
    async def initialize(self):
        """
        Initialize Moshi models, AI client, conversation loop, and load current persona.

        Raises:
            RuntimeError: If Moshi fails to initialize
            ValueError: If no persona is set or no AI API key
        """
        # Get current persona
        self.current_persona = self.persona_manager.get_current_persona()
        if not self.current_persona:
            raise ValueError("No persona set in PersonaManager")
        # Initialize Moshi with quality setting
        try:
            self.moshi = MoshiBridge(quality=self.moshi_quality)
            print(f"✅ Moshi initialized (quality: {self.moshi.quality})")
        except Exception as e:
            self._set_state(ConversationState.ERROR)
            raise RuntimeError(f"Failed to initialize Moshi: {e}")
        # Initialize AI client
        try:
            self.ai_client = AIClient(self.config)
            print(f"✅ AI client initialized")
        except Exception as e:
            self._set_state(ConversationState.ERROR)
            raise RuntimeError(f"Failed to initialize AI client: {e}")
        # Initialize memory manager
        await self.memory_manager.initialize()
        # Create conversation loop
        self.conversation_loop = ConversationLoop(
            moshi_bridge=self.moshi,
            persona_manager=self.persona_manager,
            memory_manager=self.memory_manager,
            ai_client=self.ai_client,
            user_id=self.user_id,
            on_turn_complete=self._on_conversation_turn,
            on_state_change=self._on_state_change
        )
        print(f"✅ Conversation loop initialized")
        # Set initial state
        self._set_state(ConversationState.IDLE)
    async def start_conversation(self):
        """
        Begin voice conversation loop.

        Starts listening for user input and processing responses.
        """
        if not self.conversation_loop:
            raise RuntimeError("Conversation loop not initialized. Call initialize() first.")
        self._running = True
        await self.conversation_loop.start()
        self._set_state(ConversationState.LISTENING)
        print("🎙️  Voice conversation started")
    async def stop_conversation(self):
        """Stop voice conversation and clean up."""
        self._running = False
        # Stop conversation loop
        if self.conversation_loop:
            await self.conversation_loop.stop()
        self._set_state(ConversationState.IDLE)
        print("🛑 Voice conversation stopped")
    async def process_audio_input(self, audio_chunk: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Process incoming user audio chunk.

        Args:
            audio_chunk: Audio samples at 24kHz (from microphone)

        Returns:
            Dict with response_audio, response_text, or None if error
        """
        if not self.moshi:
            raise RuntimeError("Moshi not initialized")
        # Update mic amplitude for visualization
        self._current_mic_amplitude = self.moshi.get_amplitude(audio_chunk)
        # Transition to THINKING state
        self._set_state(ConversationState.THINKING)
        try:
            # Get conversation context from memory
            history = await self.memory_manager.get_conversation_history(
                self.user_id,
                limit=10
            )
            # Build system prompt with persona + history
            system_prompt = self._build_prompt_with_history(history)
            # Generate response with Moshi
            response_audio, response_text = self.moshi.generate_response(
                user_audio=audio_chunk,
                text_prompt=system_prompt,
                max_frames=125  # ~10 seconds
            )
            # Update Moshi amplitude for visualization
            self._current_moshi_amplitude = self.moshi.get_amplitude(response_audio)
            # Store in memory (user input is transcribed by Moshi, so we use response_text as user)
            # NOTE: Moshi returns both user and assistant text, we need to separate
            # For now, store the full interaction
            await self.memory_manager.store_message(
                user_id=self.user_id,
                message="[Audio input]",  # Placeholder - Moshi doesn't transcribe user
                role="user",
                metadata={"persona": self.current_persona.name}
            )
            # Store assistant response
            await self.memory_manager.store_message(
                user_id=self.user_id,
                message=response_text,
                role="assistant",
                metadata={"persona": self.current_persona.name}
            )
            # Transition to SPEAKING state
            self._set_state(ConversationState.SPEAKING)
            # Add to audio buffer for streaming
            self._audio_buffer.append(response_audio)
            return {
                "response_audio": response_audio,
                "response_text": response_text,
                "mic_amplitude": self._current_mic_amplitude,
                "moshi_amplitude": self._current_moshi_amplitude
            }
        except Exception as e:
            print(f"❌ Error processing audio: {e}")
            self._set_state(ConversationState.ERROR)
            return None
        finally:
            # Return to LISTENING state after processing
            if self._running:
                self._set_state(ConversationState.LISTENING)
    async def generate_response(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Generate AI response from text (for text-based testing).

        Args:
            text: User text input

        Returns:
            Dict with response_text or None if error
        """
        # This is a simplified version for text-only interaction
        # In full implementation, this would call an LLM API
        # For now, just store in memory and return placeholder
        await self.memory_manager.store_message(
            user_id=self.user_id,
            message=text,
            role="user"
        )
        # Build system prompt
        history = await self.memory_manager.get_conversation_history(
            self.user_id,
            limit=10
        )
        system_prompt = self._build_prompt_with_history(history)
        # TODO: Call LLM API here (OpenAI, Anthropic, etc.)
        # For now, return echo response
        response_text = f"[{self.current_persona.name}]: I heard you say: {text}"
        # Store response
        await self.memory_manager.store_message(
            user_id=self.user_id,
            message=response_text,
            role="assistant",
            metadata={"persona": self.current_persona.name}
        )
        return {"response_text": response_text}
    def get_audio_stream(self) -> AsyncGenerator[np.ndarray, None]:
        """
        Get audio stream generator for visualizer.

        Yields:
            Audio chunks from buffer
        """
        async def stream():
            while self._running or self._audio_buffer:
                if self._audio_buffer:
                    chunk = self._audio_buffer.pop(0)
                    yield chunk
                else:
                    await asyncio.sleep(0.01)  # 10ms polling
        return stream()
    def get_conversation_state(self) -> ConversationState:
        """Get current conversation state."""
        return self.state
    def get_amplitudes(self) -> Dict[str, float]:
        """
        Get current audio amplitudes for visualization.

        Returns:
            Dict with mic_amplitude and moshi_amplitude (0.0 - 1.0)
        """
        if self.conversation_loop:
            return self.conversation_loop.get_amplitudes()
        return {
            "mic_amplitude": self._current_mic_amplitude,
            "moshi_amplitude": self._current_moshi_amplitude
        }
    def on_state_change(self, callback):
        """
        Register callback for state changes.

        Args:
            callback: Function called with new state
        """
        self.state_callbacks.append(callback)
    async def switch_persona(self, persona_name: str) -> bool:
        """
        Switch to a different persona.

        Args:
            persona_name: Name of persona to switch to

        Returns:
            True if switch successful
        """
        success = self.persona_manager.set_current_persona(persona_name)
        if success:
            self.current_persona = self.persona_manager.get_current_persona()
            # NOTE: Moshi voice settings are baked into the model
            # Switching personas only changes system prompt and theme
            print(f"✅ Switched to persona: {persona_name}")
            return True
        return False
    async def reload_persona(self) -> bool:
        """
        Reload current persona from disk (for hot-reloading).

        Returns:
            True if reload successful
        """
        if not self.current_persona:
            return False
        success = self.persona_manager.reload_persona(self.current_persona.name)
        if success:
            self.current_persona = self.persona_manager.get_current_persona()
            print(f"✅ Reloaded persona: {self.current_persona.name}")
            return True
        return False
    async def clear_conversation_history(self):
        """Clear conversation history for current user."""
        await self.memory_manager.clear_history(self.user_id)
        print("🗑️  Conversation history cleared")
    # Private methods
    def _build_prompt_with_history(self, history: str) -> str:
        """
        Build system prompt with persona + conversation history.

        Args:
            history: Formatted conversation history

        Returns:
            Complete system prompt
        """
        persona_prompt = self.current_persona.build_system_prompt(include_personality=True)
        if history:
            return f"{persona_prompt}\n\n## Recent Conversation\n{history}"
        return persona_prompt
    def _set_state(self, new_state: ConversationState):
        """
        Set conversation state and notify callbacks.

        Args:
            new_state: New conversation state
        """
        if self.state != new_state:
            self.state = new_state
            # Notify callbacks
            for callback in self.state_callbacks:
                try:
                    callback(new_state)
                except Exception as e:
                    print(f"⚠️  State callback error: {e}")
    async def cleanup(self):
        """Clean up resources (call before shutdown)."""
        await self.stop_conversation()
        await self.memory_manager.close()
        print("🧹 Voice bridge cleaned up")
    def _on_conversation_turn(self, turn: ConversationTurn):
        """
        Callback when conversation turn completes.
        Args:
            turn: ConversationTurn object with full turn data
        """
        print(f"👤 User: {turn.user_text}")
        print(f"🤖 {turn.persona_name}: {turn.assistant_text}")
        # Update amplitudes for visualization
        if turn.metadata:
            self._current_mic_amplitude = turn.metadata.get("mic_amplitude", 0.0)
            self._current_moshi_amplitude = turn.metadata.get("moshi_amplitude", 0.0)
    def _on_state_change(self, state: str):
        """
        Callback when conversation state changes.
        Args:
            state: New state string ("idle", "listening", "thinking", "speaking")
        """
        # Map string states to ConversationState enum
        state_map = {
            "idle": ConversationState.IDLE,
            "listening": ConversationState.LISTENING,
            "thinking": ConversationState.THINKING,
            "speaking": ConversationState.SPEAKING,
            "error": ConversationState.ERROR
        }
        new_state = state_map.get(state, ConversationState.IDLE)
        self._set_state(new_state)
