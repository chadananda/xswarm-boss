"""
WebSocket server for voice communication with xSwarm Rust core
"""

import asyncio
import logging
import json
from typing import Optional
import websockets
from websockets.server import WebSocketServerProtocol
import numpy as np

from .bridge import VoiceBridge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceServer:
    """
    WebSocket server for real-time voice communication.

    Protocol:
    - Binary frames: PCM audio data (24kHz, mono, float32)
    - Text frames: JSON control messages
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        model_repo: str = "kyutai/moshika-mlx-q4",
    ):
        self.host = host
        self.port = port
        self.bridge = VoiceBridge(model_repo=model_repo)
        self.server: Optional[websockets.WebSocketServer] = None

    async def handle_client(self, websocket: WebSocketServerProtocol):
        """
        Handle a single WebSocket client connection.

        Args:
            websocket: WebSocket connection
        """
        client_addr = websocket.remote_address
        logger.info(f"Client connected: {client_addr}")

        try:
            # Initialize MOSHI on first connection
            await self.bridge.initialize()

            # Send ready message
            await websocket.send(json.dumps({
                "type": "ready",
                "model": self.bridge.model_repo,
                "sample_rate": self.bridge.sample_rate,
            }))

            # Handle incoming messages
            async for message in websocket:
                if isinstance(message, bytes):
                    # Binary: Audio data
                    await self.handle_audio(websocket, message)
                else:
                    # Text: Control message
                    await self.handle_control(websocket, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_addr}")
        except Exception as e:
            logger.error(f"Error handling client {client_addr}: {e}")
        finally:
            logger.info(f"Cleaning up client: {client_addr}")

    async def handle_audio(self, websocket: WebSocketServerProtocol, data: bytes):
        """
        Handle incoming audio data.

        Args:
            websocket: WebSocket connection
            data: Raw PCM audio bytes
        """
        # Convert bytes to numpy array (float32, 24kHz mono)
        audio = np.frombuffer(data, dtype=np.float32)

        # Process through MOSHI
        async for response_chunk in self.bridge.process_audio(audio):
            # Send audio response back
            await websocket.send(response_chunk.tobytes())

    async def handle_control(self, websocket: WebSocketServerProtocol, message: str):
        """
        Handle control messages.

        Args:
            websocket: WebSocket connection
            message: JSON control message
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

            elif msg_type == "synthesize":
                # Text-to-speech request
                text = data.get("text", "")
                async for audio_chunk in self.bridge.synthesize_text(text):
                    await websocket.send(audio_chunk.tobytes())

            elif msg_type == "config":
                # Update configuration
                personality = data.get("personality")
                if personality:
                    self.bridge.personality = personality
                    logger.info(f"Updated personality: {personality}")

            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {message}")
        except Exception as e:
            logger.error(f"Error handling control message: {e}")

    async def start(self):
        """Start the WebSocket server."""
        logger.info(f"Starting voice server on ws://{self.host}:{self.port}")

        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
        )

        logger.info(f"Voice server started successfully")

    async def stop(self):
        """Stop the WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.bridge.cleanup()
            logger.info("Voice server stopped")

    async def run(self):
        """Run the server indefinitely."""
        await self.start()

        # Run until interrupted
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await self.stop()


async def main():
    """Main entry point for standalone server."""
    import argparse

    parser = argparse.ArgumentParser(description="xSwarm Voice Server")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument(
        "--model",
        default="kyutai/moshika-mlx-q4",
        help="MOSHI model repository"
    )

    args = parser.parse_args()

    server = VoiceServer(
        host=args.host,
        port=args.port,
        model_repo=args.model,
    )

    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
