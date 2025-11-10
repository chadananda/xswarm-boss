#!/usr/bin/env python3
"""
Test audio files with Vosk (traditional ASR that won't hallucinate).
If audio is garbled, Vosk will return empty or nonsense - it won't invent plausible text.
"""

import wave
import json
import sys
import os
from vosk import Model, KaldiRecognizer

def download_model_if_needed():
    """Download small English model if not present."""
    model_path = os.path.expanduser("~/.cache/vosk/vosk-model-small-en-us-0.15")

    if not os.path.exists(model_path):
        print("📥 Downloading Vosk model (first time only, ~40MB)...")
        import zipfile
        import urllib.request

        model_url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
        cache_dir = os.path.expanduser("~/.cache/vosk")
        os.makedirs(cache_dir, exist_ok=True)

        zip_path = os.path.join(cache_dir, "model.zip")
        urllib.request.urlretrieve(model_url, zip_path)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(cache_dir)

        os.remove(zip_path)
        print(f"✅ Model downloaded to {model_path}")

    return model_path

def transcribe_audio(audio_file):
    """Transcribe audio with Vosk (won't hallucinate)."""
    print(f"\n🎤 Testing: {audio_file}")
    print("━" * 60)

    if not os.path.exists(audio_file):
        print(f"❌ File not found: {audio_file}")
        return None

    # Get model
    model_path = download_model_if_needed()
    model = Model(model_path)

    # Open WAV file
    wf = wave.open(audio_file, "rb")

    # Check format
    print(f"Format: {wf.getnchannels()} channel(s), {wf.getframerate()} Hz, {wf.getsampwidth() * 8}-bit")

    if wf.getnchannels() != 1:
        print("⚠️  WARNING: Vosk works best with mono audio")

    # Create recognizer
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    # Process audio
    results = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            if result.get('text'):
                results.append(result['text'])

    # Get final result
    final = json.loads(rec.FinalResult())
    if final.get('text'):
        results.append(final['text'])

    # Combine all text
    full_text = ' '.join(results).strip()

    print(f"\n📝 Transcription: \"{full_text}\"")
    print(f"📊 Word count: {len(full_text.split())}")
    print(f"📊 Character count: {len(full_text)}")

    # Analyze result
    if not full_text:
        print("🔴 RESULT: NO SPEECH DETECTED - Audio is likely garbled or silent")
        return "GARBLED"
    elif len(full_text.split()) < 3:
        print("🟡 RESULT: Very few words - Audio might be garbled or unclear")
        return "UNCLEAR"
    else:
        print("🟢 RESULT: Clear speech detected")
        return "CLEAR"

    return full_text

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test-audio-with-vosk.py <audio_file.wav> [audio_file2.wav ...]")
        print("\nExample:")
        print("  python3 test-audio-with-vosk.py ./tmp/moshi-response.wav")
        sys.exit(1)

    print("🧪 VOSK Audio Quality Test")
    print("Vosk is a traditional ASR - it won't hallucinate like Whisper")
    print("If audio is garbled, Vosk will return empty or nonsense")
    print("=" * 60)

    results = {}
    for audio_file in sys.argv[1:]:
        result = transcribe_audio(audio_file)
        results[audio_file] = result

    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    for audio_file, result in results.items():
        filename = os.path.basename(audio_file)
        print(f"{filename}: {result}")
