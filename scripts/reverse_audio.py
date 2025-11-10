#!/usr/bin/env python3
"""Test if MOSHI garbled audio is actually reversed."""
import wave
import numpy as np
import sys

def reverse_wav(input_path, output_path):
    with wave.open(input_path, 'rb') as wav_in:
        params = wav_in.getparams()
        sampwidth = params.sampwidth
        n_frames = params.nframes
        
        frames = wav_in.readframes(n_frames)
        
        if sampwidth == 2:
            dtype = np.int16
        else:
            raise ValueError(f"Unsupported sample width: {sampwidth}")
        
        samples = np.frombuffer(frames, dtype=dtype)
        reversed_samples = samples[::-1]
    
    with wave.open(output_path, 'wb') as wav_out:
        wav_out.setparams(params)
        wav_out.writeframes(reversed_samples.tobytes())
    
    print(f"✅ Reversed: {input_path} → {output_path}")
    print(f"   Samples: {len(samples)}")

if __name__ == "__main__":
    reverse_wav(sys.argv[1], sys.argv[2])
