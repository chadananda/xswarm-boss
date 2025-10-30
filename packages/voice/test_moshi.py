#!/usr/bin/env python3
"""
Quick test script for MOSHI voice integration
"""

import asyncio
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_model_loading():
    """Test MOSHI model loading"""
    from xswarm_voice import VoiceBridge
    import numpy as np

    logger.info("=" * 60)
    logger.info("MOSHI Voice Bridge Test")
    logger.info("=" * 60)

    # Create bridge
    logger.info("\n1. Creating VoiceBridge...")
    bridge = VoiceBridge(
        model_repo="kyutai/moshika-mlx-q4",
        sample_rate=24000
    )

    # Initialize (downloads model if needed)
    logger.info("\n2. Initializing MOSHI model...")
    logger.info("   (This will download ~4GB on first run)")
    try:
        await bridge.initialize()
        logger.info("   ✓ Model loaded successfully!")
    except Exception as e:
        logger.error(f"   ✗ Failed to load model: {e}")
        return False

    # Test audio processing
    logger.info("\n3. Testing audio processing...")
    try:
        # Create 1 second of silence as test input
        test_audio = np.zeros(24000, dtype=np.float32)
        logger.info(f"   Input: {test_audio.shape} samples (1 second @ 24kHz)")

        # Process through MOSHI
        response_chunks = []
        async for chunk in bridge.process_audio(test_audio):
            response_chunks.append(chunk)
            logger.info(f"   Received chunk: {chunk.shape}")

        total_samples = sum(len(chunk) for chunk in response_chunks)
        logger.info(f"   ✓ Processed {total_samples} output samples")

    except Exception as e:
        logger.error(f"   ✗ Audio processing failed: {e}")
        return False

    # Test text synthesis
    logger.info("\n4. Testing text-to-speech...")
    try:
        test_text = "Hello from MOSHI"
        logger.info(f"   Text: '{test_text}'")

        response_chunks = []
        async for chunk in bridge.synthesize_text(test_text):
            response_chunks.append(chunk)

        total_samples = sum(len(chunk) for chunk in response_chunks)
        logger.info(f"   ✓ Generated {total_samples} audio samples")

    except Exception as e:
        logger.error(f"   ✗ Text synthesis failed: {e}")
        return False

    # Cleanup
    logger.info("\n5. Cleaning up...")
    bridge.cleanup()
    logger.info("   ✓ Done")

    logger.info("\n" + "=" * 60)
    logger.info("✓ ALL TESTS PASSED")
    logger.info("=" * 60)
    return True


async def test_server():
    """Test WebSocket server"""
    from xswarm_voice import VoiceServer

    logger.info("=" * 60)
    logger.info("MOSHI WebSocket Server Test")
    logger.info("=" * 60)

    server = VoiceServer(
        host="localhost",
        port=8765,
        model_repo="kyutai/moshika-mlx-q4"
    )

    logger.info("\n1. Starting WebSocket server on ws://localhost:8765...")
    await server.start()
    logger.info("   ✓ Server started successfully!")

    logger.info("\n2. Server is running. Press Ctrl+C to stop.")
    logger.info("   You can now connect a WebSocket client to test audio streaming.")

    try:
        # Run until interrupted
        await asyncio.Future()
    except KeyboardInterrupt:
        logger.info("\n\nShutting down server...")
        await server.stop()
        logger.info("✓ Server stopped")


async def main():
    """Main test runner"""
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        # Test WebSocket server
        await test_server()
    else:
        # Test model loading and basic functionality
        success = await test_model_loading()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("xSwarm Voice Bridge - MOSHI Test Suite")
    print("=" * 60)
    print("\nUsage:")
    print("  python3 test_moshi.py          # Test model loading")
    print("  python3 test_moshi.py server   # Test WebSocket server")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
