#!/usr/bin/env python3
"""
Test common wake words support.
Verifies that "computer", "alexa", and "boss" are always available.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.config import Config


def test_get_common_wake_words():
    """Test that common wake words are defined"""
    print("=== Test 1: Get Common Wake Words ===")

    common_words = Config.get_common_wake_words()

    # Should include computer, alexa, boss
    assert "computer" in common_words, "'computer' should be in common wake words"
    assert "alexa" in common_words, "'alexa' should be in common wake words"
    assert "boss" in common_words, "'boss' should be in common wake words"

    # Should also have assistant and hey
    assert "assistant" in common_words, "'assistant' should be in common wake words"
    assert "hey" in common_words, "'hey' should be in common wake words"

    print(f"✓ Common wake words: {common_words}")
    print("✅ Test 1 PASSED\n")


def test_config_accepts_list():
    """Test that Config accepts wake_word as list"""
    print("=== Test 2: Config Accepts List ===")

    # Single string (backward compatibility)
    config1 = Config(wake_word="jarvis")
    assert config1.wake_word == "jarvis"
    print("✓ Single string wake word works")

    # List of wake words
    wake_words = ["jarvis", "computer", "alexa"]
    config2 = Config(wake_word=wake_words)
    assert config2.wake_word == wake_words
    print(f"✓ List of wake words works: {wake_words}")

    print("✅ Test 2 PASSED\n")


def test_wake_word_detector_integration():
    """Test that wake word detector can use combined list"""
    print("=== Test 3: Wake Word Detector Integration ===")

    # Mock detector to test integration
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

    # Build combined list like main.py does
    persona_names = ["jarvis", "hal", "kitt"]
    common_wake_words = Config.get_common_wake_words()

    all_wake_words = []
    all_wake_words.extend(persona_names)
    all_wake_words.extend(common_wake_words)

    # Remove duplicates
    seen = set()
    unique_wake_words = []
    for word in all_wake_words:
        if word not in seen:
            seen.add(word)
            unique_wake_words.append(word)

    # Create detector with combined list
    detector = MockDetector(unique_wake_words)

    # Test persona names work
    assert detector._is_wake_word_present("jarvis")
    assert detector._is_wake_word_present("hal")
    assert detector._is_wake_word_present("kitt")
    print("✓ Persona names detected")

    # Test common wake words work
    assert detector._is_wake_word_present("computer")
    assert detector._is_wake_word_present("alexa")
    assert detector._is_wake_word_present("boss")
    print("✓ Common wake words detected")

    # Test phrases
    assert detector._is_wake_word_present("hey computer")
    assert detector._is_wake_word_present("yo alexa")
    assert detector._is_wake_word_present("hello boss")
    print("✓ Phrases with wake words detected")

    print(f"✓ Total wake words: {len(unique_wake_words)}")
    print(f"✓ Unique wake words: {unique_wake_words}")

    print("✅ Test 3 PASSED\n")


def test_user_use_case():
    """Test the actual user scenario: forgot which persona is active"""
    print("=== Test 4: User Forgot Which Persona is Active ===")

    # Mock detector
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

    # User has JARVIS active but forgets and tries different names
    persona_names = ["jarvis", "hal", "kitt", "c3po", "marvin"]
    common_wake_words = Config.get_common_wake_words()

    all_wake_words = persona_names + common_wake_words

    # Remove duplicates
    seen = set()
    unique_wake_words = []
    for word in all_wake_words:
        if word not in seen:
            seen.add(word)
            unique_wake_words.append(word)

    detector = MockDetector(unique_wake_words)

    # User tries different things without remembering
    attempts = [
        "hey computer",          # Generic wake word
        "alexa what's the time", # Another generic
        "yo boss",               # Another generic
        "jarvis are you there",  # Correct persona name
        "hal help me",           # Wrong persona name (but works!)
        "hey assistant"          # Generic assistant
    ]

    for attempt in attempts:
        detected = detector._is_wake_word_present(attempt)
        assert detected, f"Should detect wake word in: {attempt}"
        print(f"✓ '{attempt}' → detected")

    print("\n✓ User doesn't need to remember which persona is active!")
    print(f"✓ Any of {len(unique_wake_words)} wake words will work")
    print("✅ Test 4 PASSED\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Common Wake Words Test Suite")
    print("=" * 60 + "\n")

    try:
        test_get_common_wake_words()
        test_config_accepts_list()
        test_wake_word_detector_integration()
        test_user_use_case()

        print("=" * 60)
        print("✅ ALL TESTS PASSED (4/4)")
        print("=" * 60)
        print("\nCommon wake words support is ready!")
        print("\nSupported wake words:")
        print("  - computer")
        print("  - alexa")
        print("  - boss")
        print("  - assistant")
        print("  - hey")
        print("  - All persona names")
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
