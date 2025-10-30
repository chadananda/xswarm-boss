"""
MOSHI Voice Bridge - Core integration layer
"""

import asyncio
import logging
import platform
from pathlib import Path
from typing import Optional, AsyncIterator
import numpy as np

from .persona import PersonaConfig, load_persona_from_config

logger = logging.getLogger(__name__)

# Platform detection for backend selection
IS_MACOS_ARM = platform.system() == "Darwin" and platform.machine() == "arm64"
IS_LINUX = platform.system() == "Linux"
IS_WINDOWS = platform.system() == "Windows"


class VoiceBridge:
    """
    Bridge between xSwarm and MOSHI voice model.

    Handles:
    - MOSHI model initialization and management
    - Audio streaming (24kHz PCM)
    - Voice synthesis with personality/theme
    - Full-duplex communication
    """

    def __init__(
        self,
        model_repo: str = "kyutai/moshika-mlx-q4",
        sample_rate: int = 24000,
        persona: Optional[str] = None,
        config_path: Optional[Path] = None,
    ):
        """
        Initialize the voice bridge.

        Args:
            model_repo: Hugging Face model repository
            sample_rate: Audio sample rate (MOSHI requires 24000Hz)
            persona: Optional persona name (e.g., "boss") or None to load from config
            config_path: Optional path to config.toml (auto-detected if None)
        """
        self.model_repo = model_repo
        self.sample_rate = sample_rate

        # Load persona configuration
        self.persona_config: Optional[PersonaConfig] = None
        try:
            if persona:
                # Load specific persona by name
                logger.info(f"Loading persona: {persona}")
                self.persona_config = PersonaConfig(persona)
            elif config_path:
                # Load persona from config file
                logger.info(f"Loading persona from config: {config_path}")
                self.persona_config = load_persona_from_config(config_path)
            else:
                # Try to auto-detect config.toml
                logger.info("Auto-detecting persona from config.toml")
                project_root = self._find_project_root()
                config_path = project_root / "config.toml"
                if config_path.exists():
                    self.persona_config = load_persona_from_config(config_path)
                else:
                    logger.warning("No config.toml found - using default persona")
        except Exception as e:
            logger.warning(f"Failed to load persona: {e}")
            logger.warning("Continuing without persona configuration")

        # MOSHI components (initialized lazily)
        self._model = None
        self._codec = None
        self._lm_gen = None  # Language model generator
        self._tokenizer = None  # Sentencepiece tokenizer

        persona_name = self.persona_config.name if self.persona_config else "default"
        logger.info(f"VoiceBridge initialized: model={model_repo}, persona={persona_name}, sr={sample_rate}")

    def _find_project_root(self) -> Path:
        """Find project root by looking for config.toml."""
        current = Path(__file__).resolve().parent
        for _ in range(10):
            if (current / "config.toml").exists():
                return current
            current = current.parent
        raise FileNotFoundError("Could not find project root (config.toml not found)")

    async def initialize(self):
        """
        Initialize MOSHI model and codec.

        This is done lazily to avoid loading the model until actually needed.
        Downloads model from Hugging Face on first run (~4GB for q4).
        """
        if self._model is not None:
            return

        persona_name = self.persona_config.name if self.persona_config else "default"
        logger.info(f"Loading MOSHI model: {self.model_repo}")
        logger.info(f"Persona: {persona_name}")
        logger.info(f"Platform: macOS ARM={IS_MACOS_ARM}, Linux={IS_LINUX}, Windows={IS_WINDOWS}")

        try:
            if IS_MACOS_ARM:
                # Use MLX backend on Apple Silicon
                from moshi_mlx import models, utils
                from huggingface_hub import hf_hub_download
                import rustymimi
                import sentencepiece
                import mlx.core as mx
                import mlx.nn as nn
                import json

                logger.info("Using MLX backend (Apple Silicon)")
                logger.info("Downloading model from Hugging Face (this may take a few minutes on first run)")

                # 1. Download and load config
                config_path = await asyncio.to_thread(
                    hf_hub_download,
                    self.model_repo,
                    "config.json"
                )
                with open(config_path) as f:
                    lm_config_dict = json.load(f)

                logger.info(f"✓ Config loaded from {self.model_repo}")

                # 2. Load model weights
                logger.info("Downloading model weights (~3.5GB)...")
                moshi_weights = await asyncio.to_thread(
                    hf_hub_download,
                    self.model_repo,
                    "model.q4.safetensors"
                )

                lm_config = models.LmConfig.from_config_dict(lm_config_dict)
                self._model = models.Lm(lm_config)
                self._model.set_dtype(mx.bfloat16)
                nn.quantize(self._model, bits=4, group_size=32)

                await asyncio.to_thread(
                    self._model.load_weights,
                    moshi_weights,
                    strict=True
                )

                logger.info(f"✓ MOSHI model loaded: {self.model_repo}")

                # 3. Load audio codec (Mimi)
                logger.info("Loading Mimi audio codec...")
                mimi_weights = await asyncio.to_thread(
                    hf_hub_download,
                    self.model_repo,
                    lm_config_dict["mimi_name"]
                )
                self._codec = rustymimi.Tokenizer(mimi_weights, num_codebooks=16)
                logger.info("✓ Mimi codec loaded")

                # 4. Load text tokenizer
                logger.info("Loading text tokenizer...")
                tokenizer_path = await asyncio.to_thread(
                    hf_hub_download,
                    self.model_repo,
                    lm_config_dict["tokenizer_name"]
                )
                self._tokenizer = sentencepiece.SentencePieceProcessor(tokenizer_path)
                logger.info("✓ Text tokenizer loaded")

                # 5. Create language model generator with persona conditioning
                conditioning_params = self.persona_config.get_conditioning_params() if self.persona_config else {}

                self._lm_gen = models.LmGen(
                    model=self._model,
                    max_steps=10000,  # Max conversation length
                    text_sampler=utils.Sampler(
                        top_k=25,
                        temp=conditioning_params.get("temperature", 0.8)
                    ),
                    audio_sampler=utils.Sampler(
                        top_k=250,
                        temp=conditioning_params.get("temperature", 0.8)
                    ),
                )

                if self.persona_config:
                    logger.info(f"✓ Persona conditioning applied: {persona_name}")
                    logger.info(f"  Voice style: {conditioning_params.get('voice_style', 'neutral')}")
                    logger.info(f"  Temperature: {conditioning_params.get('temperature', 0.8)}")
                    logger.info(f"  Speaking pace: {conditioning_params.get('speaking_pace', 'moderate')}")
                else:
                    logger.info("✓ Using default parameters (no persona)")

                logger.info(f"✓ Sample rate: {self.sample_rate}Hz")
                logger.info(f"✓ MOSHI ready for inference!")

            else:
                # For Linux/Windows, would use PyTorch backend
                # TODO: Implement PyTorch backend for cross-platform support
                logger.error("PyTorch backend not yet implemented for Linux/Windows")
                logger.error("MOSHI currently only supports macOS with Apple Silicon (MLX)")
                raise NotImplementedError(
                    "MOSHI voice is currently only available on macOS with Apple Silicon. "
                    "Cross-platform support (PyTorch backend) coming soon."
                )

        except ImportError as e:
            logger.error(f"Failed to import MOSHI dependencies: {e}")
            logger.error("Please install: pip install -e packages/voice")
            raise
        except Exception as e:
            logger.error(f"Failed to load MOSHI model: {e}")
            raise

    async def process_audio(
        self,
        audio_chunk: np.ndarray,
    ) -> AsyncIterator[np.ndarray]:
        """
        Process incoming audio through MOSHI.

        Args:
            audio_chunk: PCM audio data (24kHz, mono, float32)

        Yields:
            Audio response chunks from MOSHI
        """
        if self._model is None:
            await self.initialize()

        logger.debug(f"Processing audio chunk: {audio_chunk.shape}")

        try:
            # Run inference in thread pool to avoid blocking event loop
            response_audio = await asyncio.to_thread(
                self._process_audio_sync,
                audio_chunk
            )

            # Stream response back in chunks
            chunk_size = self.sample_rate // 10  # 100ms chunks
            for i in range(0, len(response_audio), chunk_size):
                chunk = response_audio[i:i + chunk_size]
                yield chunk

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            # Return silence on error
            yield np.zeros(len(audio_chunk), dtype=np.float32)

    def _process_audio_sync(self, audio: np.ndarray) -> np.ndarray:
        """
        Synchronous audio processing (runs in thread pool).

        Process audio in 80ms chunks (1920 samples at 24kHz).

        Args:
            audio: Input audio array (24kHz PCM float32)

        Returns:
            Output audio array (24kHz PCM float32)
        """
        if self._model is None or self._codec is None or self._lm_gen is None:
            logger.warning("Model not initialized, returning silence")
            return np.zeros_like(audio)

        try:
            import mlx.core as mx

            # MOSHI processes audio in 80ms chunks (1920 samples at 24kHz)
            # Ensure input is correct size
            if len(audio) != 1920:
                logger.warning(f"Audio chunk size {len(audio)} != 1920, padding/trimming")
                if len(audio) < 1920:
                    # Pad with zeros
                    padding = np.zeros(1920 - len(audio), dtype=np.float32)
                    audio = np.concatenate([audio, padding])
                else:
                    # Trim to 1920
                    audio = audio[:1920]

            # 1. Encode input audio with rustymimi
            logger.debug(f"Encoding audio: shape={audio.shape}")
            # rustymimi expects (batch, samples) format
            audio_tokens = self._codec.encode_step(audio[None, :])  # Add batch dimension
            audio_tokens = mx.array(audio_tokens).transpose(0, 2, 1)[:, :, :8]
            logger.debug(f"Encoded to audio tokens: shape={audio_tokens.shape}")

            # 2. Run through MOSHI language model
            logger.debug("Running MOSHI inference...")
            text_token = self._lm_gen.step(audio_tokens[0])  # Remove batch dim

            # Get generated audio tokens
            output_tokens = self._lm_gen.last_audio_tokens()

            # 3. Decode response tokens back to audio
            if output_tokens is not None:
                logger.debug("Decoding response audio...")
                # Convert MLX array to numpy for rustymimi
                output_tokens_np = np.array(output_tokens[:, :, None]).astype(np.uint32)
                response_audio = self._codec.decode_step(output_tokens_np)

                # Ensure output is 1920 samples
                if len(response_audio) < 1920:
                    padding = np.zeros(1920 - len(response_audio), dtype=np.float32)
                    response_audio = np.concatenate([response_audio, padding])
                elif len(response_audio) > 1920:
                    response_audio = response_audio[:1920]

                logger.debug(f"Output audio shape: {response_audio.shape}")
                return response_audio
            else:
                # No output yet, return silence
                logger.debug("No output tokens yet, returning silence")
                return np.zeros(1920, dtype=np.float32)

        except Exception as e:
            logger.error(f"MOSHI inference error: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return silence on error to avoid breaking the stream
            return np.zeros(1920, dtype=np.float32)

    async def synthesize_text(
        self,
        text: str,
    ) -> AsyncIterator[np.ndarray]:
        """
        Synthesize text to speech using MOSHI.

        Args:
            text: Text to synthesize

        Yields:
            Audio chunks (24kHz PCM)
        """
        if self._model is None:
            await self.initialize()

        logger.info(f"Synthesizing text: {text[:50]}...")

        try:
            # For text synthesis, we use the language model to generate audio
            # MOSHI can be prompted with text in the conditioning
            # For now, generate speech-like response

            # This is a simplified implementation
            # Full implementation would:
            # 1. Convert text to tokens using sentencepiece
            # 2. Generate audio tokens from text tokens
            # 3. Decode audio tokens to waveform

            # Generate silence for now with proper length based on text
            # Roughly 0.15 seconds per word (typical speech rate)
            words = len(text.split())
            duration_seconds = max(1.0, words * 0.15)
            num_samples = int(self.sample_rate * duration_seconds)

            # Yield in chunks
            chunk_size = self.sample_rate // 10  # 100ms chunks
            for i in range(0, num_samples, chunk_size):
                chunk = np.zeros(min(chunk_size, num_samples - i), dtype=np.float32)
                yield chunk

        except Exception as e:
            logger.error(f"Text synthesis error: {e}")
            # Yield 1 second of silence on error
            yield np.zeros(self.sample_rate, dtype=np.float32)

    def cleanup(self):
        """Clean up resources."""
        self._model = None
        self._codec = None
        self._lm_gen = None
        self._tokenizer = None
        self.persona_config = None
        logger.info("VoiceBridge cleaned up")
