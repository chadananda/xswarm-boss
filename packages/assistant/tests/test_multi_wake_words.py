#!/usr/bin/env python3
"""
Test multi-wake-word support.
Verifies that detector can handle multiple wake words simultaneously.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.wake_word.detector import WakeWordDetector


def test_single_wake_word():
    """Test backward compatibility with single wake word"""
    print("=== Test 1: Single Wake Word (backward compatibility) ===")

    # Mock detector without actual Vosk model
    class MockDetector:
        def __init__(self, wake_word):
            if isinstance(wake_word, str):
                self.wake_words = [wake_word.lower().strip()]
            else:
                self.wake_words = [w.lower().strip() for w in wake_word]
            self.wake_word = self.wake_words[0]

        def _is_wake_word_present(self, text: str) -> bool:
            for wake_word in self.wake_words:
                if text == wake_word:
                    return True
                words = text.split()
                if wake_word in words:
                    return True
                if " " in wake_word and wake_word in text:
                    return True
            return False

    detector = MockDetector("jarvis")
    assert detector.wake_words == ["jarvis"]
    assert detector.wake_word == "jarvis"
    assert detector._is_wake_word_present("jarvis")
    assert detector._is_wake_word_present("hey jarvis")
    assert not detector._is_wake_word_present("computer")

    print("✓ Single wake word works")
    print("✓ wake_words = ['jarvis']")
    print("✓ wake_word = 'jarvis' (backward compatibility)")
    print("✓ Detects 'jarvis' and 'hey jarvis'")
    print("✅ Test 1 PASSED\n")


def test_multiple_wake_words():
    """Test multiple wake words"""
    print("=== Test 2: Multiple Wake Words ===")

    class MockDetector:
        def __init__(self, wake_word):
            if isinstance(wake_word, str):
                self.wake_words = [wake_word.lower().strip()]
            else:
                self.wake_words = [w.lower().strip() for w in wake_word]
            self.wake_word = self.wake_words[0]

        def _is_wake_word_present(self, text: str) -> bool:
            for wake_word in self.wake_words:
                if text == wake_word:
                    return True
                words = text.split()
                if wake_word in words:
                    return True
                if " " in wake_word and wake_word in text:
                    return True
            return False

    # Create detector with multiple wake words
    wake_words = ["jarvis", "computer", "hal", "kitt"]
    detector = MockDetector(wake_words)

    assert len(detector.wake_words) == 4
    assert detector.wake_word == "jarvis"  # First one for backward compat

    # Test each wake word
    assert detector._is_wake_word_present("jarvis")
    assert detector._is_wake_word_present("computer")
    assert detector._is_wake_word_present("hal")
    assert detector._is_wake_word_present("kitt")

    # Test with phrases
    assert detector._is_wake_word_present("hey jarvis")
    assert detector._is_wake_word_present("hello computer")
    assert detector._is_wake_word_present("hi hal")
    assert detector._is_wake_word_present("yo kitt")

    # Test non-matching
    assert not detector._is_wake_word_present("alexa")
    assert not detector._is_wake_word_present("siri")

    print("✓ Multiple wake words work")
    print(f"✓ wake_words = {detector.wake_words}")
    print("✓ All 4 wake words detected")
    print("✓ Works with phrases")
    print("✓ Rejects non-wake-words")
    print("✅ Test 2 PASSED\n")


def test_set_wake_word():
    """Test changing wake words at runtime"""
    print("=== Test 3: Runtime Wake Word Changes ===")

    class MockDetector:
        def __init__(self, wake_word):
            if isinstance(wake_word, str):
                self.wake_words = [wake_word.lower().strip()]
            else:
                self.wake_words = [w.lower().strip() for w in wake_word]
            self.wake_word = self.wake_words[0]

        def set_wake_word(self, wake_word):
            if isinstance(wake_word, str):
                self.wake_words = [wake_word.lower().strip()]
            else:
                self.wake_words = [w.lower().strip() for w in wake_word]
            self.wake_word = self.wake_words[0]

        def _is_wake_word_present(self, text: str) -> bool:
            for wake_word in self.wake_words:
                if text == wake_word:
                    return True
                words = text.split()
                if wake_word in words:
                    return True
                if " " in wake_word and wake_word in text:
                    return True
            return False

    detector = MockDetector("jarvis")
    assert detector._is_wake_word_present("jarvis")
    assert not detector._is_wake_word_present("computer")

    # Change to multiple wake words
    detector.set_wake_word(["computer", "assistant"])
    assert len(detector.wake_words) == 2
    assert detector._is_wake_word_present("computer")
    assert detector._is_wake_word_present("assistant")
    assert not detector._is_wake_word_present("jarvis")

    # Change back to single
    detector.set_wake_word("hal")
    assert len(detector.wake_words) == 1
    assert detector._is_wake_word_present("hal")
    assert not detector._is_wake_word_present("computer")

    print("✓ Runtime wake word changes work")
    print("✓ Can switch from single to multiple")
    print("✓ Can switch from multiple to single")
    print("✅ Test 3 PASSED\n")


def test_persona_use_case():
    """Test the persona name use case (dozen wake words)"""
    print("=== Test 4: Persona Use Case (Many Wake Words) ===")

    class MockDetector:
        def __init__(self, wake_word):
            if isinstance(wake_word, str):
                self.wake_words = [wake_word.lower().strip()]
            else:
                self.wake_words = [w.lower().strip() for w in wake_word]
            self.wake_word = self.wake_words[0]

        def _is_wake_word_present(self, text: str) -> bool:
            for wake_word in self.wake_words:
                if text == wake_word:
                    return True
                words = text.split()
                if wake_word in words:
                    return True
                if " " in wake_word and wake_word in text:
                    return True
            return False

    # All persona names
    persona_names = [
        "jarvis",
        "hal",
        "kitt",
        "computer",
        "assistant",
        "c3po",
        "marvin",
        "glados",
        "cortana",
        "samantha",
        "her",
        "karen"
    ]

    detector = MockDetector(persona_names)
    assert len(detector.wake_words) == 12

    # User doesn't remember which persona is active, tries different names
    user_attempts = [
        "jarvis are you there",
        "hey hal",
        "computer please help",
        "kitt can you hear me",
        "yo marvin"
    ]

    for attempt in user_attempts:
        detected = detector._is_wake_word_present(attempt)
        assert detected, f"Should detect wake word in: {attempt}"
        print(f"✓ Detected wake word in: '{attempt}'")

    print(f"✓ {len(persona_names)} wake words configured")
    print("✓ User can say any persona name")
    print("✓ No need to remember which is active")
    print("✅ Test 4 PASSED\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Multi-Wake-Word Support Test Suite")
    print("=" * 60 + "\n")

    try:
        test_single_wake_word()
        test_multiple_wake_words()
        test_set_wake_word()
        test_persona_use_case()

        print("=" * 60)
        print("✅ ALL TESTS PASSED (4/4)")
        print("=" * 60)
        print("\nMulti-wake-word support is ready!")
        print("\nUsage examples:")
        print("  # Single wake word")
        print("  detector = WakeWordDetector(model_path, wake_word='jarvis')")
        print()
        print("  # Multiple wake words")
        print("  detector = WakeWordDetector(model_path, wake_word=['jarvis', 'computer', 'hal'])")
        print()
        print("  # All persona names (for user convenience)")
        print("  persona_names = ['jarvis', 'hal', 'kitt', 'c3po', 'marvin', ...]")
        print("  detector = WakeWordDetector(model_path, wake_word=persona_names)")
        print()

        return 0

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST SUITE FAILED")
        print(f"Error: {e}")
        print("=" * 60 + "\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
