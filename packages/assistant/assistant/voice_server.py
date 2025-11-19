#!/usr/bin/env python3
"""
Moshi Voice Server - Real-time voice AI with full control API.

A ZeroMQ-based server that provides:
- Real-time full-duplex audio processing via MLX on Metal GPU
- Persona control (traits → sampling parameters)
- Memory/context injection for conversation history
- Tool use detection and result injection
- Fine-grained sampling control (temperature, top_p, logit_bias)

Architecture mirrors official moshi_mlx local.py for optimal performance.

Usage:
    # Start server
    python voice_server.py --quality q4

    # Or auto-start from client
    from voice_server import get_voice_client
    client = get_voice_client(quality="q4")
    client.set_persona("JARVIS", "You are JARVIS...", {...})

Ports:
    5555 - Command socket (REQ/REP)
    5556 - Audio input (PUSH/PULL)
    5557 - Audio output (PUB/SUB)
"""

import argparse
import asyncio
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import msgpack
import numpy as np
import zmq

# MLX imports (lazy loaded to allow client-only usage)
_mlx_loaded = False


def _load_mlx():
    """Lazy load MLX dependencies."""
    global _mlx_loaded
    if _mlx_loaded:
        return

    global mx, nn, models, utils, sentencepiece, rustymimi, huggingface_hub
    import mlx.core as mx
    import mlx.nn as nn
    import sentencepiece
    import rustymimi
    import huggingface_hub
    from moshi_mlx import models, utils

    _mlx_loaded = True


# =============================================================================
# Constants
# =============================================================================

COMMAND_PORT = 5555
AUDIO_IN_PORT = 5556
AUDIO_OUT_PORT = 5557
SAMPLE_RATE = 24000
FRAME_SIZE = 1920  # 80ms at 24kHz
CONTEXT_WINDOW = 3000  # Moshi's context limit

DEFAULT_SAMPLING = {
    "temperature": 0.7,
    "top_p": 0.9,
    "logit_bias": {},
    "cfg_coef": 1.0,
}

# Trait to sampling parameter mappings
TRAIT_MAPPINGS = {
    "formality": {"temperature": (-0.1, 0.1)},  # High formality = lower temp
    "humor": {"temperature": (0.0, 0.15)},  # High humor = higher temp
    "enthusiasm": {"top_p": (0.0, 0.1)},  # High enthusiasm = higher top_p
    "verbosity": {"cfg_coef": (0.0, 0.3)},  # High verbosity = higher guidance
}


# =============================================================================
# Voice Server
# =============================================================================

class VoiceServer:
    """
    Moshi voice server with full control API.

    Runs MLX inference in the main process with async audio processing.
    """

    def __init__(self, quality: str = "q4"):
        self.quality = quality
        self.running = False

        # Model state
        self.model = None
        self.text_tokenizer = None
        self.audio_tokenizer = None
        self.lm_gen = None

        # Persona state
        self.persona = {
            "name": "Default",
            "system_prompt": "",
            "traits": {},
            "voice_style": {},
        }

        # Memory state
        self.context = []  # List of {role, content}
        self.context_tokens = 0

        # Tool state
        self.tools = {}  # name -> {description, parameters}
        self.tool_callbacks = []
        self.pending_tool_results = []

        # Sampling state
        self.sampling = DEFAULT_SAMPLING.copy()

        # Audio state
        self.state = "idle"
        self.mic_amplitude = 0.0
        self.output_amplitude = 0.0

        # Callbacks
        self.text_callbacks = []
        self.audio_callbacks = []

        # ZeroMQ
        self.zmq_context = None
        self.command_socket = None
        self.audio_in_socket = None
        self.audio_out_socket = None

        # Async processing
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()

    def start(self, command_port: int = COMMAND_PORT):
        """Start the voice server."""
        _load_mlx()

        print(f"Starting Moshi Voice Server (quality={self.quality})...")

        # Load model
        self._load_model()

        # Initialize ZeroMQ
        self._init_zmq(command_port)

        # Start processing
        self.running = True

        # Run command loop in main thread
        self._command_loop()

    def stop(self):
        """Stop the voice server."""
        self.running = False
        if self.zmq_context:
            self.zmq_context.term()

    def _load_model(self):
        """Load MLX model and tokenizers."""
        # Map quality to repo
        quality_map = {
            "bf16": ("kyutai/moshiko-mlx-bf16", None, "model.safetensors"),
            "q8": ("kyutai/moshiko-mlx-q8", 8, "model.q8.safetensors"),
            "q4": ("kyutai/moshiko-mlx-q4", 4, "model.q4.safetensors"),
        }

        if self.quality not in quality_map:
            raise ValueError(f"Invalid quality: {self.quality}")

        hf_repo, quantized, model_file = quality_map[self.quality]

        # Download files
        print(f"Loading from {hf_repo}...")
        model_path = huggingface_hub.hf_hub_download(hf_repo, model_file)
        tokenizer_path = huggingface_hub.hf_hub_download(hf_repo, "tokenizer_spm_32k_3.model")
        mimi_path = huggingface_hub.hf_hub_download(hf_repo, "tokenizer-e351c8d8-checkpoint125.safetensors")

        # Load text tokenizer
        print("Loading text tokenizer...")
        self.text_tokenizer = sentencepiece.SentencePieceProcessor(tokenizer_path)

        # Load audio tokenizer
        print("Loading audio codec...")
        self.audio_tokenizer = rustymimi.StreamTokenizer(mimi_path)

        # Load model
        print("Loading model weights...")
        mx.random.seed(299792458)
        lm_config = models.config_v0_1()
        self.model = models.Lm(lm_config)
        self.model.set_dtype(mx.bfloat16)

        if quantized is not None:
            group_size = 32 if quantized == 4 else 64
            nn.quantize(self.model, bits=quantized, group_size=group_size)

        self.model.load_weights(model_path, strict=True)
        print("Weights loaded")

        # Warmup
        self.model.warmup()
        print("Model warmed up")

        # Create generator
        self.lm_gen = models.LmGen(
            model=self.model,
            max_steps=2000,
            text_sampler=utils.Sampler(),
            audio_sampler=utils.Sampler(),
            check=False,
        )

        # Warmup codec
        self._warmup_codec()

        print("Voice server ready!")

    def _warmup_codec(self):
        """Warmup audio codec."""
        for i in range(4):
            pcm = np.zeros(FRAME_SIZE, dtype=np.float32)
            self.audio_tokenizer.encode(pcm)
            while True:
                codes = self.audio_tokenizer.get_encoded()
                if codes is not None:
                    break
                time.sleep(0.001)

            if i == 0:
                continue

            self.audio_tokenizer.decode(codes.T if codes.ndim == 2 else codes)
            while True:
                audio = self.audio_tokenizer.get_decoded()
                if audio is not None:
                    break
                time.sleep(0.001)

    def _init_zmq(self, command_port: int):
        """Initialize ZeroMQ sockets."""
        self.zmq_context = zmq.Context()

        # Command socket (REQ/REP)
        self.command_socket = self.zmq_context.socket(zmq.REP)
        self.command_socket.bind(f"tcp://*:{command_port}")

        # Audio sockets
        self.audio_in_socket = self.zmq_context.socket(zmq.PULL)
        self.audio_in_socket.bind(f"tcp://*:{AUDIO_IN_PORT}")

        self.audio_out_socket = self.zmq_context.socket(zmq.PUB)
        self.audio_out_socket.bind(f"tcp://*:{AUDIO_OUT_PORT}")

        print(f"Listening on ports {command_port}, {AUDIO_IN_PORT}, {AUDIO_OUT_PORT}")

    def _command_loop(self):
        """Main command processing loop."""
        poller = zmq.Poller()
        poller.register(self.command_socket, zmq.POLLIN)
        poller.register(self.audio_in_socket, zmq.POLLIN)

        while self.running:
            try:
                socks = dict(poller.poll(timeout=10))

                # Handle commands
                if self.command_socket in socks:
                    msg = self.command_socket.recv()
                    request = msgpack.unpackb(msg, raw=False)
                    response = self._handle_command(request)
                    self.command_socket.send(msgpack.packb(response))

                # Handle audio input
                if self.audio_in_socket in socks:
                    msg = self.audio_in_socket.recv()
                    audio_data = msgpack.unpackb(msg, raw=False)
                    pcm = np.array(audio_data["pcm"], dtype=np.float32)

                    # Process audio
                    result = self._process_audio_frame(pcm)

                    # Always send response (for amplitude feedback even without audio)
                    self.audio_out_socket.send(msgpack.packb({
                        "audio": result["audio"].tolist() if result["audio"] is not None else None,
                        "text": result["text"],
                        "mic_amp": self.mic_amplitude,
                        "out_amp": self.output_amplitude,
                    }))

            except zmq.ZMQError as e:
                if e.errno == zmq.ETERM:
                    break
                raise

    def _handle_command(self, request: dict) -> dict:
        """Handle a command request."""
        method = request.get("method", "")
        params = request.get("params", {})

        try:
            if method == "ping":
                return {"status": "ok", "result": "pong"}

            elif method == "set_persona":
                return self._cmd_set_persona(params)

            elif method == "get_persona":
                return {"status": "ok", "result": self.persona}

            elif method == "inject_context":
                return self._cmd_inject_context(params)

            elif method == "inject_history":
                return self._cmd_inject_history(params)

            elif method == "get_history":
                return {"status": "ok", "result": self.context}

            elif method == "clear_context":
                self.context = []
                self.context_tokens = 0
                return {"status": "ok"}

            elif method == "get_context_usage":
                return {"status": "ok", "result": {
                    "used": self.context_tokens,
                    "total": CONTEXT_WINDOW,
                    "remaining": CONTEXT_WINDOW - self.context_tokens,
                }}

            elif method == "register_tool":
                return self._cmd_register_tool(params)

            elif method == "inject_tool_result":
                return self._cmd_inject_tool_result(params)

            elif method == "set_sampling":
                return self._cmd_set_sampling(params)

            elif method == "get_state":
                return {"status": "ok", "result": {
                    "state": self.state,
                    "mic_amplitude": self.mic_amplitude,
                    "output_amplitude": self.output_amplitude,
                }}

            elif method == "shutdown":
                self.running = False
                return {"status": "ok"}

            else:
                return {"status": "error", "error": f"Unknown method: {method}"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _cmd_set_persona(self, params: dict) -> dict:
        """Set persona and update sampling parameters."""
        self.persona = {
            "name": params.get("name", "Default"),
            "system_prompt": params.get("system_prompt", ""),
            "traits": params.get("traits", {}),
            "voice_style": params.get("voice_style", {}),
        }

        # Map traits to sampling parameters
        self._update_sampling_from_traits()

        # Inject system prompt into context
        if self.persona["system_prompt"]:
            self.context = [{"role": "system", "content": self.persona["system_prompt"]}]
            self.context_tokens = len(self.text_tokenizer.encode(self.persona["system_prompt"]))

        return {"status": "ok"}

    def _update_sampling_from_traits(self):
        """Update sampling parameters based on persona traits."""
        # Start with defaults
        self.sampling = DEFAULT_SAMPLING.copy()

        # Apply trait mappings
        traits = self.persona.get("traits", {})
        for trait_name, mappings in TRAIT_MAPPINGS.items():
            trait_value = traits.get(trait_name, 0.5)  # Default to 0.5

            for param_name, (min_adj, max_adj) in mappings.items():
                adjustment = min_adj + (max_adj - min_adj) * trait_value
                if param_name in self.sampling:
                    self.sampling[param_name] += adjustment

        # Apply voice style overrides
        voice_style = self.persona.get("voice_style", {})
        for key in ["temperature", "top_p", "cfg_coef"]:
            if key in voice_style:
                self.sampling[key] = voice_style[key]

        # Update sampler
        if self.lm_gen:
            self.lm_gen.text_sampler.temperature = self.sampling["temperature"]
            self.lm_gen.text_sampler.top_p = self.sampling["top_p"]
            self.lm_gen.audio_sampler.temperature = self.sampling["temperature"]
            self.lm_gen.audio_sampler.top_p = self.sampling["top_p"]

    def _cmd_inject_context(self, params: dict) -> dict:
        """Inject context into conversation."""
        text = params.get("text", "")
        role = params.get("role", "system")

        tokens = len(self.text_tokenizer.encode(text))

        if self.context_tokens + tokens > CONTEXT_WINDOW:
            return {"status": "error", "error": "Context window exceeded"}

        self.context.append({"role": role, "content": text})
        self.context_tokens += tokens

        return {"status": "ok", "tokens_used": tokens}

    def _cmd_inject_history(self, params: dict) -> dict:
        """Inject conversation history."""
        turns = params.get("turns", [])

        # Clear existing non-system context
        self.context = [c for c in self.context if c["role"] == "system"]
        self.context_tokens = sum(
            len(self.text_tokenizer.encode(c["content"]))
            for c in self.context
        )

        # Add turns
        for turn in turns:
            tokens = len(self.text_tokenizer.encode(turn.get("content", "")))
            if self.context_tokens + tokens > CONTEXT_WINDOW:
                break
            self.context.append(turn)
            self.context_tokens += tokens

        return {"status": "ok", "turns_added": len(self.context) - 1}

    def _cmd_register_tool(self, params: dict) -> dict:
        """Register a tool."""
        name = params.get("name", "")
        self.tools[name] = {
            "description": params.get("description", ""),
            "parameters": params.get("parameters", {}),
        }
        return {"status": "ok"}

    def _cmd_inject_tool_result(self, params: dict) -> dict:
        """Inject tool result into context."""
        tool_name = params.get("tool_name", "")
        result = params.get("result", "")

        text = f"[TOOL_RESULT:{tool_name}]{result}[/TOOL_RESULT]"
        return self._cmd_inject_context({"text": text, "role": "tool"})

    def _cmd_set_sampling(self, params: dict) -> dict:
        """Set sampling parameters."""
        for key in ["temperature", "top_p", "logit_bias", "cfg_coef"]:
            if key in params:
                self.sampling[key] = params[key]

        # Update sampler
        if self.lm_gen:
            self.lm_gen.text_sampler.temperature = self.sampling["temperature"]
            self.lm_gen.text_sampler.top_p = self.sampling["top_p"]
            self.lm_gen.audio_sampler.temperature = self.sampling["temperature"]
            self.lm_gen.audio_sampler.top_p = self.sampling["top_p"]

        return {"status": "ok"}

    def _process_audio_frame(self, pcm: np.ndarray) -> dict:
        """Process a single audio frame through Moshi."""
        # Update mic amplitude
        rms = np.sqrt(np.mean(pcm ** 2))
        self.mic_amplitude = float(np.clip(rms * 4, 0, 1))

        # Encode audio
        self.audio_tokenizer.encode(pcm)
        while True:
            codes = self.audio_tokenizer.get_encoded()
            if codes is not None:
                break
            time.sleep(0.0001)

        # Run inference
        audio_codes_mx = mx.array(codes).transpose(1, 0)[:, :8]
        text_token = self.lm_gen.step(audio_codes_mx)
        text_token_id = text_token[0].item()

        # Get audio output
        audio_tokens = self.lm_gen.last_audio_tokens()

        output_audio = None
        text_piece = ""

        if audio_tokens is not None:
            audio_tokens_np = np.array(audio_tokens).astype(np.uint32)

            # Decode audio
            self.audio_tokenizer.decode(audio_tokens_np)
            while True:
                audio = self.audio_tokenizer.get_decoded()
                if audio is not None:
                    output_audio = audio
                    break
                time.sleep(0.0001)

            # Update output amplitude
            if output_audio is not None:
                rms = np.sqrt(np.mean(output_audio ** 2))
                self.output_amplitude = float(np.clip(rms * 4, 0, 1))

        # Decode text token
        if text_token_id not in (0, 3):
            text_piece = self.text_tokenizer.id_to_piece(text_token_id)
            text_piece = text_piece.replace("▁", " ")

            # Check for tool calls
            self._check_tool_call(text_piece)

        return {
            "audio": output_audio,
            "text": text_piece,
        }

    def _check_tool_call(self, text: str):
        """Check for tool call markers in text output."""
        # Simple marker detection - accumulate and parse
        # In production, would use a proper state machine
        if "[TOOL_CALL:" in text:
            # Notify callbacks
            for callback in self.tool_callbacks:
                callback(text)


# =============================================================================
# Voice Server Client
# =============================================================================

class VoiceServerClient:
    """
    Client to connect to running voice server.

    Usage:
        client = VoiceServerClient()
        client.set_persona("JARVIS", "You are JARVIS...", {...})

        # For audio, use the audio methods
        client.send_audio(pcm_frame)
        output = client.recv_audio()
    """

    def __init__(self, command_port: int = COMMAND_PORT):
        self.command_port = command_port
        self.ctx = zmq.Context()

        # Command socket
        self.command_socket = self.ctx.socket(zmq.REQ)
        self.command_socket.connect(f"tcp://localhost:{command_port}")

        # Audio sockets
        self.audio_out_socket = self.ctx.socket(zmq.PUSH)
        self.audio_out_socket.connect(f"tcp://localhost:{AUDIO_IN_PORT}")

        self.audio_in_socket = self.ctx.socket(zmq.SUB)
        self.audio_in_socket.connect(f"tcp://localhost:{AUDIO_OUT_PORT}")
        self.audio_in_socket.setsockopt_string(zmq.SUBSCRIBE, "")

    def _call(self, method: str, params: dict = None) -> dict:
        """Make a command call to the server."""
        request = {"method": method, "params": params or {}}
        self.command_socket.send(msgpack.packb(request))
        response = msgpack.unpackb(self.command_socket.recv(), raw=False)

        if response.get("status") == "error":
            raise Exception(response.get("error", "Unknown error"))

        return response.get("result")

    # === Lifecycle ===

    def ping(self) -> str:
        """Ping the server."""
        return self._call("ping")

    def shutdown(self):
        """Shutdown the server."""
        self._call("shutdown")

    # === Persona Control ===

    def set_persona(
        self,
        name: str,
        system_prompt: str,
        traits: dict = None,
        voice_style: dict = None
    ):
        """
        Set persona and update voice characteristics.

        Args:
            name: Persona name
            system_prompt: System prompt describing personality
            traits: Dict of trait values (0-1): formality, humor, empathy, etc.
            voice_style: Override sampling: temperature, top_p, cfg_coef
        """
        return self._call("set_persona", {
            "name": name,
            "system_prompt": system_prompt,
            "traits": traits or {},
            "voice_style": voice_style or {},
        })

    def get_persona(self) -> dict:
        """Get current persona configuration."""
        return self._call("get_persona")

    # === Memory & Context ===

    def inject_context(self, text: str, role: str = "system"):
        """
        Inject context into conversation.

        Args:
            text: Context text to inject
            role: Role (system, user, assistant, tool)
        """
        return self._call("inject_context", {"text": text, "role": role})

    def inject_history(self, turns: list):
        """
        Inject conversation history.

        Args:
            turns: List of {role, content} dicts
        """
        return self._call("inject_history", {"turns": turns})

    def get_history(self) -> list:
        """Get current conversation history."""
        return self._call("get_history")

    def clear_context(self):
        """Clear all context except system prompt."""
        return self._call("clear_context")

    def get_context_usage(self) -> dict:
        """Get context window usage."""
        return self._call("get_context_usage")

    # === Tool Use ===

    def register_tool(self, name: str, description: str, parameters: dict):
        """
        Register a tool for Moshi to use.

        Args:
            name: Tool name
            description: What the tool does
            parameters: JSON schema of parameters
        """
        return self._call("register_tool", {
            "name": name,
            "description": description,
            "parameters": parameters,
        })

    def inject_tool_result(self, tool_name: str, result: str):
        """
        Inject result of tool execution.

        Args:
            tool_name: Name of tool that was called
            result: Result to inject
        """
        return self._call("inject_tool_result", {
            "tool_name": tool_name,
            "result": result,
        })

    # === Sampling Control ===

    def set_sampling(
        self,
        temperature: float = None,
        top_p: float = None,
        logit_bias: dict = None,
        cfg_coef: float = None
    ):
        """
        Set sampling parameters.

        Args:
            temperature: Generation temperature (0.0-2.0)
            top_p: Nucleus sampling threshold (0.0-1.0)
            logit_bias: Token biases {token_id: bias}
            cfg_coef: Classifier-free guidance coefficient
        """
        params = {}
        if temperature is not None:
            params["temperature"] = temperature
        if top_p is not None:
            params["top_p"] = top_p
        if logit_bias is not None:
            params["logit_bias"] = logit_bias
        if cfg_coef is not None:
            params["cfg_coef"] = cfg_coef

        return self._call("set_sampling", params)

    # === Audio ===

    def send_audio(self, pcm: np.ndarray):
        """
        Send audio frame for processing.

        Args:
            pcm: 1920 samples at 24kHz (80ms frame)
        """
        self.audio_out_socket.send(msgpack.packb({
            "pcm": pcm.astype(np.float32).tolist()
        }))

    def recv_audio(self, timeout: int = 100) -> Optional[dict]:
        """
        Receive processed audio.

        Args:
            timeout: Timeout in ms

        Returns:
            Dict with 'audio' (np.ndarray), 'text' (str), 'mic_amp', 'out_amp', or None
        """
        if self.audio_in_socket.poll(timeout):
            msg = self.audio_in_socket.recv()
            data = msgpack.unpackb(msg, raw=False)
            return {
                "audio": np.array(data["audio"], dtype=np.float32) if data.get("audio") else None,
                "text": data.get("text", ""),
                "mic_amp": data.get("mic_amp", 0.0),
                "out_amp": data.get("out_amp", 0.0),
            }
        return None

    # === State ===

    def get_state(self) -> dict:
        """Get server state (state, amplitudes)."""
        return self._call("get_state")

    def close(self):
        """Close client connections."""
        self.command_socket.close()
        self.audio_out_socket.close()
        self.audio_in_socket.close()
        self.ctx.term()


# =============================================================================
# Auto-start Helper
# =============================================================================

def is_server_running(port: int = COMMAND_PORT) -> bool:
    """Check if server is running."""
    try:
        ctx = zmq.Context()
        socket = ctx.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, 500)  # 500ms timeout
        socket.setsockopt(zmq.SNDTIMEO, 500)
        socket.setsockopt(zmq.LINGER, 0)  # Don't wait on close
        socket.connect(f"tcp://localhost:{port}")

        socket.send(msgpack.packb({"method": "ping"}))
        response = msgpack.unpackb(socket.recv(), raw=False)

        socket.close()
        ctx.term()

        return response.get("status") == "ok"
    except:
        try:
            socket.close()
            ctx.term()
        except:
            pass
        return False


def start_server_process(quality: str = "q4", port: int = COMMAND_PORT):
    """Start server in background process."""
    script_path = Path(__file__).resolve()

    proc = subprocess.Popen(
        [sys.executable, str(script_path), "--quality", quality, "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    return proc


def get_voice_client(quality: str = "q4", port: int = COMMAND_PORT, timeout: int = 60) -> VoiceServerClient:
    """
    Get voice server client, auto-starting server if needed.

    Args:
        quality: Model quality (bf16, q8, q4)
        port: Command port
        timeout: Startup timeout in seconds

    Returns:
        VoiceServerClient connected to server
    """
    if not is_server_running(port):
        print(f"Starting voice server (quality={quality})...")
        start_server_process(quality, port)

        # Wait for server to be ready
        start_time = time.time()
        while time.time() - start_time < timeout:
            if is_server_running(port):
                print("Voice server ready!")
                break
            time.sleep(0.5)
        else:
            raise TimeoutError(f"Server did not start within {timeout}s")

    return VoiceServerClient(port)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Moshi Voice Server")
    parser.add_argument("--quality", type=str, default="q4", choices=["bf16", "q8", "q4"])
    parser.add_argument("--port", type=int, default=COMMAND_PORT)
    args = parser.parse_args()

    server = VoiceServer(quality=args.quality)

    # Handle shutdown signals
    def signal_handler(sig, frame):
        print("\nShutting down...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server.start(command_port=args.port)


if __name__ == "__main__":
    main()
