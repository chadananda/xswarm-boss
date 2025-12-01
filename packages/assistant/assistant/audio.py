"""
Core Audio Module.
Consolidated from previous voice/audio_io.py and voice/vad.py.
Includes:
- Audio I/O (SoundDevice)
- Voice Activity Detection (Energy-based & Hybrid Silero)
"""

import logging
import sounddevice as sd
import numpy as np
import torch
import threading
import random
from typing import Callable, Optional, Dict
from queue import Queue, Empty

logger = logging.getLogger(__name__)

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
            # DISABLED: User requested system default.
            self.input_device_index = None
            # for i, dev in enumerate(devices):
            #     if dev['max_input_channels'] > 0:
            #         name = dev['name']
            #         # self.log(f"  - [{i}] {name}") # Too verbose?
            #         if "Built-in Microphone" in name or "MacBook Pro Microphone" in name:
            #             self.input_device_index = i
            #             self.log(f"🎤 Selected Input Device: {name} (Index {i})")
            #             break
            
            if self.input_device_index is None:
                self.log(f"🎤 Using Default Input: {default_in['name']}")
                self.input_device_index = default_in['index']
                
        except Exception as e:
            self.log(f"⚠️ Error querying audio devices: {e}")
            self.input_device_index = None

        # Log default output device
        try:
            default_out = sd.query_devices(kind='output')
            self.log(f"🔊 Default Output Device: {default_out['name']} (Index {default_out['index']})")
        except Exception as e:
            self.log(f"⚠️ Error querying output device: {e}")

        # Buffer state for callback
        self.current_chunk = None
        self.chunk_pos = 0

    def log(self, msg: str):
        if self.log_callback:
            self.log_callback(msg)
        else:
            logger.debug(msg)

    def start_input(self, callback: Optional[Callable] = None):
        def audio_callback(indata, frames, time, status):
            if status:
                self.log(f"⚠️ Audio Status: {status}")
            try:
                # FEEDBACK PREVENTION: Ignore mic input when output is playing
                # This prevents Moshi from hearing himself speak
                if hasattr(self, 'current_output_amplitude') and self.current_output_amplitude > 0.01:
                    # Output is playing - ignore mic input to prevent feedback
                    return
                
                audio = np.ascontiguousarray(indata[:, 0], dtype=np.float32)
                
                # DEBUG: Check for signal
                rms = np.sqrt(np.mean(audio**2))
                if rms == 0.0:
                    self.log(f"⚠️ Absolute Silence (RMS=0.0) - Check Permissions/Mute")
                
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
            latency='low',
            callback=audio_callback,
            device=self.input_device_index
        )
        self.input_stream.start()

    def start_output(self):
        self.output_queue = Queue(maxsize=100)
        # Initialize buffer state
        self.current_chunk = None
        self.chunk_pos = 0
        self.current_output_amplitude = 0.0  # Real-time amplitude from playing audio
        self._callback_count = 0
        
        def audio_callback(outdata, frames, time, status):
            if status:
                logging.warning(f"Audio callback status: {status}")
            
            try:
                self._callback_count += 1
                # Debug: Log occasionally
                if self._callback_count % 100 == 0:
                    queue_size = self.output_queue.qsize()
                    logging.debug(f"🔊 Callback #{self._callback_count}, Queue: {queue_size}, Chunk: {self.current_chunk is not None}")
                
                # Fill output buffer by piecing together chunks from queue
                needed = frames
                output = np.zeros(frames, dtype=np.float32)
                filled = 0
                
                while filled < needed:
                    # Pre-buffering logic:
                    # If we are starving (queue empty and no current chunk), wait until we have enough chunks
                    # to avoid jittery playback.
                    if self.current_chunk is None and self.output_queue.empty():
                        # Queue is empty.
                        break
                    
                    # STRICT PRE-BUFFERING:
                    # If we are just starting or recovered from starvation, don't play until we have a buffer.
                    # 3 chunks = 3 * 80ms = 240ms buffer.
                    if self.current_chunk is None and self.output_queue.qsize() < 3:
                         # Not enough data to guarantee smooth playback. Output silence.
                         break

                    # Get or continue current chunk
                    if self.current_chunk is None:
                        try:
                            self.current_chunk = self.output_queue.get_nowait()
                            self.chunk_pos = 0
                        except Exception:  # Catch Empty or any queue exception
                            break
                    
                    # Copy what we can from current chunk
                    chunk_remaining = len(self.current_chunk) - self.chunk_pos
                    to_copy = min(needed - filled, chunk_remaining)
                    
                    output[filled:filled + to_copy] = self.current_chunk[self.chunk_pos:self.chunk_pos + to_copy]
                    
                    filled += to_copy
                    self.chunk_pos += to_copy
                    
                    # If we consumed the whole chunk, clear it
                    if self.chunk_pos >= len(self.current_chunk):
                        self.current_chunk = None
                
                # Write to output
                outdata[:] = output.reshape(-1, 1)
                
                # Calculate real-time amplitude from playing audio
                if filled > 0:
                    rms = np.sqrt(np.mean(output[:filled] ** 2))
                    self.current_output_amplitude = float(rms)
                else:
                    self.current_output_amplitude = 0.0
                
            except Exception as e:
                logging.error(f"Audio callback error: {e}")
                import traceback
                logging.error(traceback.format_exc())
                outdata.fill(0)

        # Pre-buffer: Wait for some data before starting stream
        # This prevents initial underrun/choppiness
        # self.log("⏳ Pre-buffering audio...") 
        # Note: sounddevice starts callback immediately, so we handle buffering inside callback or just accept initial silence.
        # Better approach: The callback plays silence until we have enough data?
        # For now, we rely on the queue.
        
        self.output_stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            blocksize=self.frame_size, # Match Moshi frame size (1920) for stability
            latency=0.1, # 100ms hardware latency
            callback=audio_callback
        )
        self.output_stream.start()

    def play_audio(self, audio: np.ndarray):
        if len(audio) == 0:
            return
        
        # Ensure float32
        audio = np.asarray(audio, dtype=np.float32)
        
        # Check for scaling issues (int16 treated as float32)
        max_val = np.max(np.abs(audio))
        if max_val > 1.5:
            self.log(f"⚠️ Audio Amplitude Warning: Max={max_val:.2f} (Likely int16/float32 mismatch). Normalizing...")
            audio = audio / 32768.0
        
        # DEBUG: Log playback occasionally
        if np.random.random() < 0.005:
            self.log(f"🔊 AudioIO.play_audio: {len(audio)} samples, Max={max_val:.4f}")
            
        # Ensure stream is active
        if self.output_stream and not self.output_stream.active:
            self.log("⚠️ Output stream inactive! Restarting...")
            try:
                self.output_stream.start()
            except Exception as e:
                self.log(f"❌ Failed to restart output stream: {e}")

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
    def __init__(self, threshold: float = 0.001, min_speech_duration: int = 5, min_silence_duration: int = 10):
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
            logger.debug(f"Failed to load Silero VAD: {e}")
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
