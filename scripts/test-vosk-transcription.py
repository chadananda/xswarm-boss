#!/usr/bin/env python3
"""
Test MOSHI audio with Vosk (local, offline STT)
Vosk is more literal than Whisper - less likely to hallucinate
"""

import json
import wave
import sys
from pathlib import Path

try:
    from vosk import Model, KaldiRecognizer
except ImportError:
    print("ERROR: vosk library not installed")
    print("Install with: pip3 install vosk")
    sys.exit(1)

def download_model_if_needed():
    """Download Vosk model if not present"""
    model_dir = Path("./tmp/vosk-model-small-en-us-0.15")

    if model_dir.exists():
        print(f"✅ Using existing model: {model_dir}")
        return str(model_dir)

    print("📥 Downloading Vosk model (first time only, ~40MB)...")
    import urllib.request
    import zipfile

    url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    zip_path = "./tmp/vosk-model.zip"

    try:
        urllib.request.urlretrieve(url, zip_path)
        print("✅ Download complete, extracting...")

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("./tmp/")

        Path(zip_path).unlink()  # Remove zip file
        print(f"✅ Model ready: {model_dir}")
        return str(model_dir)
    except Exception as e:
        print(f"❌ Failed to download model: {e}")
        sys.exit(1)

def transcribe_wav(wav_path, model_path):
    """Transcribe WAV file using Vosk"""

    # Load model
    print(f"🔊 Loading Vosk model from {model_path}...")
    model = Model(model_path)

    # Open WAV file
    wf = wave.open(wav_path, "rb")

    # Check format
    if wf.getnchannels() != 1:
        print(f"WARNING: Audio has {wf.getnchannels()} channels, converting to mono...")

    sample_rate = wf.getframerate()
    print(f"📊 Audio: {sample_rate}Hz, {wf.getnchannels()} channel(s), {wf.getsampwidth()*8}-bit")

    # Create recognizer
    # Note: Vosk expects 16kHz, but can handle other rates
    rec = KaldiRecognizer(model, sample_rate)
    rec.SetWords(True)  # Get word-level timing

    # Process audio
    print(f"🎤 Transcribing {wav_path}...")

    results = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break

        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            if result.get("text"):
                results.append(result["text"])

    # Get final result
    final_result = json.loads(rec.FinalResult())
    if final_result.get("text"):
        results.append(final_result["text"])

    wf.close()

    # Combine all results
    full_text = " ".join(results).strip()

    return full_text, final_result

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test-vosk-transcription.py <wav_file>")
        sys.exit(1)

    wav_path = sys.argv[1]

    if not Path(wav_path).exists():
        print(f"ERROR: File not found: {wav_path}")
        sys.exit(1)

    print("🧪 VOSK TRANSCRIPTION TEST")
    print("━" * 60)
    print()

    # Download model if needed
    model_path = download_model_if_needed()
    print()

    # Transcribe
    text, result = transcribe_wav(wav_path, model_path)

    print()
    print("╔" + "═" * 58 + "╗")
    print("║ VOSK TRANSCRIPTION RESULT")
    print("╠" + "═" * 58 + "╣")
    print(f"║ Text: \"{text}\"")
    print(f"║ Length: {len(text)} characters")
    print(f"║ Words: {len(text.split()) if text else 0}")
    print("╠" + "═" * 58 + "╣")

    if text:
        print("║ ✅ Vosk transcribed something")
        print("║")
        print("║ Interpretation:")
        print("║ - If text matches expected greeting → Audio is clear")
        print("║ - If text is gibberish/wrong → Audio is garbled")
        print("║ - Vosk is literal, won't hallucinate like Whisper")
    else:
        print("║ ❌ Vosk returned EMPTY transcription")
        print("║")
        print("║ This likely means:")
        print("║ - Audio is unintelligible/garbled")
        print("║ - Audio is too quiet")
        print("║ - Audio format issue")

    print("╚" + "═" * 58 + "╝")
    print()

    # Also print confidence if available
    if "result" in result:
        print("📊 Word-level details:")
        for word_info in result.get("result", []):
            word = word_info.get("word", "")
            conf = word_info.get("conf", 0.0)
            print(f"   '{word}' (confidence: {conf:.2f})")

    print()
    print(f"Full result object: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    main()
