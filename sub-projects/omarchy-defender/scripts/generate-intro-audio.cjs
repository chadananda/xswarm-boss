/**
 * Generate intro audio assets for Omarchy Defender
 *
 * Required audio files:
 * - intro-music.mp3 - Epic cinematic background music
 * - sfx-stamp.mp3 - Rubber stamp impact sound
 * - intro-narration.mp3 - Dramatic baritone narration
 *
 * Uses:
 * - ElevenLabs API for narration (requires ELEVENLABS_API_KEY)
 * - Web Audio API / ffmpeg for sound effects
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

// Load .env from project root
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const AUDIO_DIR = path.join(__dirname, '../assets/audio');
const MANIFEST_PATH = path.join(AUDIO_DIR, 'audio-manifest.json');

// Load narration settings from manifest (single source of truth)
function loadNarrationSettings() {
  const manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
  const narration = manifest.categories.splash.find(item => item.id === 'intro-narration');

  if (!narration) {
    throw new Error('intro-narration not found in audio manifest');
  }

  return {
    text: narration.text,
    voice_id: narration.voice,
    voiceName: narration.voiceName,
    model_id: 'eleven_multilingual_v2',
    voice_settings: narration.settings || {
      stability: 0.70,
      similarity_boost: 0.80,
      style: 0.4,
      use_speaker_boost: true
    }
  };
}

async function generateNarration() {
  const apiKey = process.env.ELEVENLABS_API_KEY;

  // Load settings from manifest (single source of truth)
  const settings = loadNarrationSettings();

  if (!apiKey) {
    console.log('ELEVENLABS_API_KEY not set. Skipping narration generation.');
    console.log('To generate narration, set the environment variable and run again.');
    console.log(`\nVoice: ${settings.voiceName} (${settings.voice_id})`);
    console.log('\nNarration text to be spoken:\n');
    console.log(settings.text);
    return false;
  }

  console.log(`Generating narration with ElevenLabs (voice: ${settings.voiceName})...`);

  const data = JSON.stringify({
    text: settings.text,
    model_id: settings.model_id,
    voice_settings: settings.voice_settings
  });

  const options = {
    hostname: 'api.elevenlabs.io',
    path: `/v1/text-to-speech/${settings.voice_id}`,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'xi-api-key': apiKey,
      'Accept': 'audio/mpeg'
    }
  };

  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      if (res.statusCode !== 200) {
        console.error(`ElevenLabs API error: ${res.statusCode}`);
        let body = '';
        res.on('data', chunk => body += chunk);
        res.on('end', () => {
          console.error(body);
          resolve(false);
        });
        return;
      }

      const outputPath = path.join(AUDIO_DIR, 'intro-narration.mp3');
      const file = fs.createWriteStream(outputPath);
      res.pipe(file);

      file.on('finish', () => {
        file.close();
        console.log(`Generated: ${outputPath}`);
        resolve(true);
      });
    });

    req.on('error', (e) => {
      console.error(`Request error: ${e.message}`);
      resolve(false);
    });

    req.write(data);
    req.end();
  });
}

// Generate a simple stamp sound using raw audio data
function generateStampSound() {
  console.log('Generating stamp sound effect...');

  // Create a simple impact sound using raw PCM data
  // This creates a punchy "thwack" sound
  const sampleRate = 44100;
  const duration = 0.15; // 150ms
  const numSamples = Math.floor(sampleRate * duration);

  // Create buffer for 16-bit mono audio
  const buffer = Buffer.alloc(44 + numSamples * 2); // WAV header + data

  // Write WAV header
  buffer.write('RIFF', 0);
  buffer.writeUInt32LE(36 + numSamples * 2, 4);
  buffer.write('WAVE', 8);
  buffer.write('fmt ', 12);
  buffer.writeUInt32LE(16, 16); // fmt chunk size
  buffer.writeUInt16LE(1, 20);  // PCM
  buffer.writeUInt16LE(1, 22);  // mono
  buffer.writeUInt32LE(sampleRate, 24);
  buffer.writeUInt32LE(sampleRate * 2, 28); // byte rate
  buffer.writeUInt16LE(2, 32);  // block align
  buffer.writeUInt16LE(16, 34); // bits per sample
  buffer.write('data', 36);
  buffer.writeUInt32LE(numSamples * 2, 40);

  // Generate impact sound
  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate;

    // Initial impact (first 20ms)
    let sample = 0;
    if (t < 0.02) {
      // Sharp attack with multiple frequencies
      const attack = Math.exp(-t * 100);
      sample = attack * (
        Math.sin(2 * Math.PI * 80 * t) * 0.5 +  // Low thump
        Math.sin(2 * Math.PI * 200 * t) * 0.3 + // Mid punch
        (Math.random() * 2 - 1) * 0.2            // Noise burst
      );
    }

    // Resonant decay (20-150ms)
    if (t >= 0.02) {
      const decay = Math.exp(-(t - 0.02) * 30);
      sample = decay * (
        Math.sin(2 * Math.PI * 60 * t) * 0.3 +  // Low resonance
        Math.sin(2 * Math.PI * 120 * t) * 0.2   // Harmonic
      );
    }

    // Convert to 16-bit integer
    const intSample = Math.max(-32768, Math.min(32767, Math.floor(sample * 32767)));
    buffer.writeInt16LE(intSample, 44 + i * 2);
  }

  const outputPath = path.join(AUDIO_DIR, 'sfx-stamp.wav');
  fs.writeFileSync(outputPath, buffer);
  console.log(`Generated: ${outputPath}`);
  console.log('Note: Convert to MP3 with: ffmpeg -i sfx-stamp.wav sfx-stamp.mp3');

  return true;
}

// Generate simple ambient intro music
function generateIntroMusic() {
  console.log('Generating intro music...');

  // Create an 80-second ambient piece
  const sampleRate = 44100;
  const duration = 80; // 80 seconds for full crawl
  const numSamples = Math.floor(sampleRate * duration);

  // Create buffer for 16-bit stereo audio
  const buffer = Buffer.alloc(44 + numSamples * 4); // WAV header + stereo data

  // Write WAV header
  buffer.write('RIFF', 0);
  buffer.writeUInt32LE(36 + numSamples * 4, 4);
  buffer.write('WAVE', 8);
  buffer.write('fmt ', 12);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);  // PCM
  buffer.writeUInt16LE(2, 22);  // stereo
  buffer.writeUInt32LE(sampleRate, 24);
  buffer.writeUInt32LE(sampleRate * 4, 28);
  buffer.writeUInt16LE(4, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write('data', 36);
  buffer.writeUInt32LE(numSamples * 4, 40);

  // Generate epic ambient drone
  console.log('Generating samples (this may take a moment)...');

  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate;

    // Fade in over first 3 seconds
    const fadeIn = Math.min(1, t / 3);
    // Fade out over last 5 seconds
    const fadeOut = t > duration - 5 ? (duration - t) / 5 : 1;
    const envelope = fadeIn * fadeOut;

    // Deep drone bass (fundamental)
    const bass = Math.sin(2 * Math.PI * 55 * t) * 0.2;  // A1

    // Slow-moving pad with slight detuning
    const lfo1 = Math.sin(2 * Math.PI * 0.1 * t);
    const lfo2 = Math.sin(2 * Math.PI * 0.07 * t);
    const pad1 = Math.sin(2 * Math.PI * (110 + lfo1 * 2) * t) * 0.15;  // A2 with vibrato
    const pad2 = Math.sin(2 * Math.PI * (165 + lfo2 * 1.5) * t) * 0.1; // E3 (fifth)
    const pad3 = Math.sin(2 * Math.PI * (220 + lfo1 * 3) * t) * 0.08;  // A3 (octave)

    // Subtle high shimmer
    const shimmer = Math.sin(2 * Math.PI * 440 * t) * Math.sin(2 * Math.PI * 0.5 * t) * 0.03;

    // Occasional low rumble pulses
    const pulse = Math.sin(2 * Math.PI * 0.05 * t);
    const rumble = (pulse > 0.8) ? Math.sin(2 * Math.PI * 40 * t) * 0.1 * (pulse - 0.8) * 5 : 0;

    // Combine all elements
    let sampleL = (bass + pad1 + pad2 + pad3 + shimmer + rumble) * envelope;
    let sampleR = (bass + pad1 * 0.9 + pad2 * 1.1 + pad3 + shimmer * 1.2 + rumble) * envelope;

    // Soft limiting
    sampleL = Math.tanh(sampleL * 1.5) * 0.7;
    sampleR = Math.tanh(sampleR * 1.5) * 0.7;

    // Convert to 16-bit integers
    const intL = Math.max(-32768, Math.min(32767, Math.floor(sampleL * 32767)));
    const intR = Math.max(-32768, Math.min(32767, Math.floor(sampleR * 32767)));

    buffer.writeInt16LE(intL, 44 + i * 4);
    buffer.writeInt16LE(intR, 44 + i * 4 + 2);

    // Progress indicator every 10 seconds
    if (i % (sampleRate * 10) === 0) {
      process.stdout.write(`\r  ${Math.floor(t)}s / ${duration}s`);
    }
  }

  console.log('\n');

  const outputPath = path.join(AUDIO_DIR, 'intro-music.wav');
  fs.writeFileSync(outputPath, buffer);
  console.log(`Generated: ${outputPath}`);
  console.log('Note: Convert to MP3 with: ffmpeg -i intro-music.wav intro-music.mp3');

  return true;
}

async function main() {
  console.log('=== Omarchy Defender Intro Audio Generator ===\n');

  // Ensure audio directory exists
  if (!fs.existsSync(AUDIO_DIR)) {
    fs.mkdirSync(AUDIO_DIR, { recursive: true });
  }

  // Generate stamp sound
  generateStampSound();
  console.log('');

  // Generate intro music
  generateIntroMusic();
  console.log('');

  // Generate narration (requires API key)
  await generateNarration();

  console.log('\n=== Done ===');
  console.log('\nNext steps:');
  console.log('1. Convert WAV files to MP3:');
  console.log('   cd src/assets/audio');
  console.log('   ffmpeg -i sfx-stamp.wav -b:a 192k sfx-stamp.mp3');
  console.log('   ffmpeg -i intro-music.wav -b:a 192k intro-music.mp3');
  console.log('');
  console.log('2. For narration, either:');
  console.log('   - Set ELEVENLABS_API_KEY and run this script again');
  console.log('   - Use another TTS service with the narration text above');
  console.log('   - Record it yourself in a dramatic baritone voice!');
}

main().catch(console.error);
