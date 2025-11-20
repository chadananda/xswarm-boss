"""
Core Audio Module.
Consolidated from previous voice/audio_io.py and voice/vad.py.
Includes:
- Audio I/O (SoundDevice)
- Voice Activity Detection (Energy-based & Hybrid Silero)
"""

import sounddevice as sd
import numpy as np
import torch
import threading
from typing import Callable, Optional, Dict
from queue import Queue

# ==============================================================================
# AUDIO I/O
# ==============================================================================

class AudioIO:
    """
    Audio I/O manager using sounddevice.
    Provides real-time audio input/output with frame-based processing.
    """
    def __init__(self, sample_rate: int = 24000, frame_size: int = 1920, channels: int = 1, log_callback: Optional[Callable[[str], None]] = None):
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.channels = channels
        self.log_callback = log_callback
        self.input_queue: Queue = Queue()
        self.output_queue: Queue = Queue()
        self.input_stream: Optional[sd.InputStream] = None
        self.output_stream: Optional[sd.OutputStream] = None
        
        # Log available devices and select best input
        try:
            devices = sd.query_devices()
            default_in = sd.query_devices(kind='input')
            self.log(f"🎤 Audio Devices found: {len(devices)}")
            
            # Smart selection: Prefer "Built-in Microphone" or "MacBook Pro Microphone"
            self.input_device_index = None
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    name = dev['name']
                    # self.log(f"  - [{i}] {name}") # Too verbose?
                    if "Built-in Microphone" in name or "MacBook Pro Microphone" in name:
                        self.input_device_index = i
                        self.log(f"🎤 Selected Input Device: {name} (Index {i})")
                        break
            
            if self.input_device_index is None:
                self.log(f"🎤 Using Default Input: {default_in['name']}")
                self.input_device_index = default_in['index']
                
        except Exception as e:
            self.log(f"⚠️ Error querying audio devices: {e}")
            self.input_device_index = None

    def log(self, msg: str):
        if self.log_callback:
            self.log_callback(msg)
        else:
            print(msg)

    def start_input(self, callback: Optional[Callable] = None):
        def audio_callback(indata, frames, time, status):
            if status:
                self.log(f"⚠️ Audio Status: {status}")
            try:
                audio = np.ascontiguousarray(indata[:, 0], dtype=np.float32)
                
                # DEBUG: Check for signal
                rms = np.sqrt(np.mean(audio**2))
                if rms > 0.01:
                    self.log(f"🎤 Signal detected! RMS: {rms:.4f}")
                
                self.input_queue.put(audio)
                if callback:
                    try:
                        callback(audio)
                    except Exception as e:
                        self.log(f"❌ Error in audio callback: {e}")
            except Exception as e:
                self.log(f"❌ Critical error in audio processing: {e}")

        self.input_stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            blocksize=self.frame_size,
            callback=audio_callback,
            device=self.input_device_index
        )
        self.input_stream.start()

    def start_output(self):
        def audio_callback(outdata, frames, time, status):
            try:
                audio = self.output_queue.get_nowait()
                if audio.dtype != np.float32:
                    audio = audio.astype(np.float32)
                if audio.shape[0] < frames:
                    audio = np.pad(audio, (0, frames - audio.shape[0]))
                try:
                    outdata[:] = audio[:frames].reshape(-1, 1)
                except ValueError:
                    outdata.fill(0)
            except Exception:
                outdata.fill(0)

        self.output_stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            blocksize=self.frame_size,
            callback=audio_callback
        )
        self.output_stream.start()

    def play_audio(self, audio: np.ndarray):
        if len(audio) == 0:
            return
        audio = np.asarray(audio, dtype=np.float32)
        if not audio.flags['C_CONTIGUOUS']:
            audio = np.ascontiguousarray(audio)
        num_frames = int(np.ceil(len(audio) / self.frame_size))
        for i in range(num_frames):
            start = i * self.frame_size
            end = min((i + 1) * self.frame_size, len(audio))
            chunk = audio[start:end].copy()
            self.output_queue.put(chunk)

    def read_frame(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        try:
            return self.input_queue.get(timeout=timeout)
        except:
            return None

    def stop(self):
        if self.input_stream:
            self.input_stream.stop()
            self.input_stream.close()
        if self.output_stream:
            self.output_stream.stop()
            self.output_stream.close()


# ==============================================================================
# VOICE ACTIVITY DETECTION
# ==============================================================================

class VoiceActivityDetector:
    """Simple energy-based VAD."""
    def __init__(self, threshold: float = 0.02, min_speech_duration: int = 5, min_silence_duration: int = 10):
        self.threshold = threshold
        self.min_speech_duration = min_speech_duration
        self.min_silence_duration = min_silence_duration
        self.is_speaking = False
        self.speech_frames = 0
        self.silence_frames = 0

    def process_frame(self, audio: np.ndarray) -> bool:
        energy = np.sqrt(np.mean(audio ** 2))
        is_voice = energy > self.threshold
        if is_voice:
            self.speech_frames += 1
            self.silence_frames = 0
            if self.speech_frames >= self.min_speech_duration:
                self.is_speaking = True
        else:
            self.silence_frames += 1
            if self.silence_frames >= self.min_silence_duration:
                self.is_speaking = False
                self.speech_frames = 0
        return self.is_speaking

    def reset(self):
        self.is_speaking = False
        self.speech_frames = 0
        self.silence_frames = 0

    def get_energy(self, audio: np.ndarray) -> float:
        return float(np.sqrt(np.mean(audio ** 2)))


class HybridVAD:
    """
    Hybrid VAD combining amplitude threshold + Silero ML model.
    Reduces false positives while maintaining low latency.
    """
    def __init__(self, sample_rate: int = 16000, amplitude_threshold: float = 0.015, silero_threshold: float = 0.5, min_speech_duration_ms: int = 250, min_silence_duration_ms: int = 500):
        self.sample_rate = sample_rate
        self.amplitude_threshold = amplitude_threshold
        self.silero_threshold = silero_threshold
        frame_ms = 30
        self.min_speech_frames = max(1, min_speech_duration_ms // frame_ms)
        self.min_silence_frames = max(1, min_silence_duration_ms // frame_ms)
        self.is_speaking = False
        self.speech_frames = 0
        self.silence_frames = 0
        self._silero_model = None
        self._silero_utils = None

    def _load_silero(self):
        if self._silero_model is not None:
            return
        try:
            model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False, onnx=False)
            self._silero_model = model
            self._silero_utils = utils
            if torch.backends.mps.is_available():
                self._silero_model = self._silero_model.to('mps')
            elif torch.cuda.is_available():
                self._silero_model = self._silero_model.to('cuda')
            self._silero_model.eval()
        except Exception as e:
            print(f"Warning: Failed to load Silero VAD: {e}")
            self._silero_model = "disabled"

    def _check_amplitude(self, audio: np.ndarray) -> bool:
        energy = np.sqrt(np.mean(audio ** 2))
        return energy > self.amplitude_threshold

    def _check_silero(self, audio: np.ndarray) -> float:
        self._load_silero()
        if self._silero_model == "disabled":
            return 1.0 if self._check_amplitude(audio) else 0.0
        try:
            audio_tensor = torch.from_numpy(audio).float()
            if hasattr(self._silero_model, 'device'):
                audio_tensor = audio_tensor.to(self._silero_model.device)
            with torch.no_grad():
                confidence = self._silero_model(audio_tensor, self.sample_rate).item()
            return confidence
        except Exception:
            return 1.0 if self._check_amplitude(audio) else 0.0

    def process_frame(self, audio: np.ndarray) -> bool:
        if not self._check_amplitude(audio):
            self.silence_frames += 1
            self.speech_frames = 0
            if self.silence_frames >= self.min_silence_frames:
                self.is_speaking = False
            return self.is_speaking

        confidence = self._check_silero(audio)
        is_voice = confidence >= self.silero_threshold
        if is_voice:
            self.speech_frames += 1
            self.silence_frames = 0
            if self.speech_frames >= self.min_speech_frames:
                self.is_speaking = True
        else:
            self.silence_frames += 1
            if self.silence_frames >= self.min_silence_frames:
                self.is_speaking = False
                self.speech_frames = 0
        return self.is_speaking

    def reset(self):
        self.is_speaking = False
        self.speech_frames = 0
        self.silence_frames = 0
        if self._silero_model and self._silero_model != "disabled":
            try:
                self._silero_model.reset_states()
            except:
                pass

    def get_stats(self) -> dict:
        return {
            "is_speaking": self.is_speaking,
            "speech_frames": self.speech_frames,
            "silence_frames": self.silence_frames,
            "silero_loaded": self._silero_model is not None and self._silero_model != "disabled",
        }
