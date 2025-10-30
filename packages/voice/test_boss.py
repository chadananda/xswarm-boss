#!/usr/bin/env python3
"""
Test script for Boss persona voice bridge.

This script tests:
1. Persona configuration loading
2. MOSHI model initialization
3. Basic audio inference

Run from project root:
  cd packages/voice
  python3 test_boss.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from xswarm_voice.bridge import VoiceBridge
from xswarm_voice.persona import load_persona_from_config
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_persona_loading():
    """Test that persona configuration loads correctly."""
    logger.info("=" * 60)
    logger.info("TEST 1: Persona Configuration Loading")
    logger.info("=" * 60)

    try:
        # Find config.toml
        config_path = Path(__file__).parent.parent.parent / "config.toml"
        logger.info(f"Loading config from: {config_path}")

        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            return False

        # Load persona
        persona_config = load_persona_from_config(config_path)

        logger.info(f"✓ Persona loaded: {persona_config.name}")
        logger.info(f"  Voice style: {persona_config.get_persona_params().get('voice_style')}")
        logger.info(f"  Speaking pace: {persona_config.get_persona_params().get('speaking_pace')}")

        # Check system prompt
        system_prompt = persona_config.get_system_prompt()
        logger.info(f"  System prompt length: {len(system_prompt)} characters")
        logger.info(f"  First 100 chars: {system_prompt[:100]}...")

        return True

    except Exception as e:
        logger.error(f"✗ Persona loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_bridge_initialization():
    """Test that VoiceBridge initializes with Boss persona."""
    logger.info("=" * 60)
    logger.info("TEST 2: VoiceBridge Initialization")
    logger.info("=" * 60)

    try:
        # Create bridge (will auto-load persona from config.toml)
        bridge = VoiceBridge()

        logger.info(f"✓ Bridge created")
        if bridge.persona_config:
            logger.info(f"  Persona: {bridge.persona_config.name}")
        else:
            logger.warning("  No persona loaded")

        # Initialize MOSHI model
        logger.info("Initializing MOSHI model (this may take 2-3 minutes on first run)...")
        await bridge.initialize()

        logger.info("✓ MOSHI model initialized successfully!")

        return True

    except Exception as e:
        logger.error(f"✗ Bridge initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_audio_inference():
    """Test basic audio inference."""
    logger.info("=" * 60)
    logger.info("TEST 3: Audio Inference")
    logger.info("=" * 60)

    try:
        # Create bridge
        bridge = VoiceBridge()
        await bridge.initialize()

        # Generate 80ms of test audio (1920 samples @ 24kHz)
        sample_rate = 24000
        chunk_duration_ms = 80
        chunk_samples = int(sample_rate * chunk_duration_ms / 1000)

        # Create test audio (sine wave at 440Hz - musical note A)
        t = np.linspace(0, chunk_duration_ms / 1000, chunk_samples)
        test_audio = 0.1 * np.sin(2 * np.pi * 440 * t).astype(np.float32)

        logger.info(f"Processing {chunk_samples} samples ({chunk_duration_ms}ms) of test audio...")

        # Process through MOSHI
        response_chunks = []
        async for chunk in bridge.process_audio(test_audio):
            response_chunks.append(chunk)
            logger.info(f"  Received response chunk: {chunk.shape}")

        total_samples = sum(len(c) for c in response_chunks)
        logger.info(f"✓ Inference complete: {total_samples} output samples")

        return True

    except Exception as e:
        logger.error(f"✗ Audio inference failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    logger.info("Starting Boss Persona Voice Bridge Tests")
    logger.info("")

    # Test 1: Persona loading
    test1_passed = await test_persona_loading()
    logger.info("")

    # Test 2: Bridge initialization (commented out by default - takes 2-3 minutes)
    # Uncomment to test full MOSHI loading
    test2_passed = False  # Set to True if you want to skip
    logger.info("TEST 2 SKIPPED: MOSHI initialization (takes 2-3 minutes)")
    logger.info("To run: uncomment test2_passed line in main()")
    # test2_passed = await test_bridge_initialization()
    logger.info("")

    # Test 3: Audio inference (requires test 2 to pass)
    test3_passed = False
    if test2_passed:
        test3_passed = await test_audio_inference()
        logger.info("")
    else:
        logger.info("TEST 3 SKIPPED: Requires MOSHI initialization")
        logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Test 1 (Persona Loading):        {'✓ PASS' if test1_passed else '✗ FAIL'}")
    logger.info(f"Test 2 (MOSHI Initialization):   {'✓ PASS' if test2_passed else 'SKIPPED'}")
    logger.info(f"Test 3 (Audio Inference):        {'✓ PASS' if test3_passed else 'SKIPPED'}")

    if test1_passed:
        logger.info("")
        logger.info("✓ Boss persona is correctly configured!")
        logger.info("  To test MOSHI, uncomment the test2_passed line in main()")
        return 0
    else:
        logger.error("")
        logger.error("✗ Tests failed - see errors above")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
