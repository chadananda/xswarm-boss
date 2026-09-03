/**
 * Video Exporter - Converts demo scripts to MP4 video
 * Uses Puppeteer to run the game headlessly and ffmpeg to encode
 */

import puppeteer from 'puppeteer';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs/promises';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Video format presets
const FORMATS = {
  full: { width: 1920, height: 1080, name: 'YouTube Full (16:9)' },
  shorts: { width: 1080, height: 1920, name: 'YouTube Shorts (9:16)' }
};

export class VideoExporter {
  constructor(options = {}) {
    this.serverUrl = options.serverUrl || 'http://localhost:3000';
    this.demoPath = options.demoPath;
    this.format = options.format || 'full';
    this.fps = options.fps || 30;
    this.outputDir = options.outputDir || path.join(__dirname, '../../tmp/videos');
    this.onProgress = options.onProgress || (() => {});
  }

  async export() {
    const formatConfig = FORMATS[this.format];
    if (!formatConfig) {
      throw new Error(`Unknown format: ${this.format}. Use 'full' or 'shorts'`);
    }

    // Ensure output directory exists
    await fs.mkdir(this.outputDir, { recursive: true });

    const sessionId = Date.now();
    const framesDir = path.join(this.outputDir, `frames_${sessionId}`);
    await fs.mkdir(framesDir, { recursive: true });

    this.onProgress({ phase: 'launch', message: 'Launching browser...' });

    const browser = await puppeteer.launch({
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        `--window-size=${formatConfig.width},${formatConfig.height}`
      ]
    });

    try {
      const page = await browser.newPage();
      await page.setViewport({
        width: formatConfig.width,
        height: formatConfig.height,
        deviceScaleFactor: 1
      });

      // Load demo JSON to get duration
      const demoUrl = `${this.serverUrl}/demos/${this.demoPath}`;
      this.onProgress({ phase: 'load', message: `Loading demo: ${this.demoPath}` });

      const demoRes = await fetch(demoUrl);
      if (!demoRes.ok) {
        throw new Error(`Failed to load demo: ${demoRes.statusText}`);
      }
      const demoData = await demoRes.json();
      const duration = demoData.duration || 60000;

      // Navigate to game with demo + record mode
      const gameUrl = `${this.serverUrl}/app/?demo=${encodeURIComponent(`/demos/${this.demoPath}`)}&record=true&seed=${demoData.seed || 42}`;

      this.onProgress({ phase: 'navigate', message: 'Loading game...' });
      await page.goto(gameUrl, { waitUntil: 'networkidle2', timeout: 30000 });

      // Wait for game to initialize
      await page.waitForFunction('window.gameReady === true', { timeout: 15000 });

      this.onProgress({ phase: 'record', message: 'Recording frames...' });

      // Calculate frame timing
      const frameInterval = 1000 / this.fps;
      const totalFrames = Math.ceil(duration / frameInterval);
      let frameCount = 0;

      // Capture frames at fixed intervals
      const startTime = Date.now();

      while (frameCount < totalFrames) {
        const framePath = path.join(framesDir, `frame_${String(frameCount).padStart(6, '0')}.png`);

        // Screenshot the game canvas
        await page.screenshot({
          path: framePath,
          type: 'png'
        });

        frameCount++;

        if (frameCount % 30 === 0) {
          const progress = Math.round((frameCount / totalFrames) * 100);
          this.onProgress({
            phase: 'record',
            message: `Recording: ${progress}%`,
            progress,
            frame: frameCount,
            totalFrames
          });
        }

        // Wait for next frame time
        const elapsed = Date.now() - startTime;
        const targetTime = frameCount * frameInterval;
        const waitTime = Math.max(0, targetTime - elapsed);

        if (waitTime > 0) {
          await new Promise(r => setTimeout(r, waitTime));
        }

        // Check if demo is complete
        const isComplete = await page.evaluate(() => window.recordingComplete === true);
        if (isComplete) {
          this.onProgress({ phase: 'record', message: 'Demo playback complete' });
          break;
        }
      }

      this.onProgress({ phase: 'encode', message: 'Encoding video...' });

      // Encode with ffmpeg
      const outputFile = `${this.demoPath.replace(/\//g, '_').replace('.json', '')}_${this.format}_${sessionId}.mp4`;
      const outputPath = path.join(this.outputDir, outputFile);

      await this.encode(framesDir, outputPath);

      // Cleanup frames
      this.onProgress({ phase: 'cleanup', message: 'Cleaning up...' });
      await fs.rm(framesDir, { recursive: true });

      this.onProgress({
        phase: 'complete',
        message: 'Export complete!',
        outputPath,
        outputFile
      });

      return {
        success: true,
        path: outputPath,
        file: outputFile,
        frames: frameCount,
        duration: Date.now() - startTime
      };

    } finally {
      await browser.close();
    }
  }

  async encode(framesDir, outputPath) {
    return new Promise((resolve, reject) => {
      const ffmpegArgs = [
        '-y', // Overwrite output
        '-framerate', String(this.fps),
        '-i', path.join(framesDir, 'frame_%06d.png'),
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', // Optimize for streaming
        outputPath
      ];

      const ffmpeg = spawn('ffmpeg', ffmpegArgs);

      let stderr = '';
      ffmpeg.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      ffmpeg.on('close', (code) => {
        if (code === 0) {
          resolve();
        } else {
          reject(new Error(`ffmpeg failed with code ${code}: ${stderr}`));
        }
      });

      ffmpeg.on('error', (err) => {
        reject(new Error(`ffmpeg error: ${err.message}`));
      });
    });
  }

  static getFormats() {
    return FORMATS;
  }
}

// CLI usage
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.log('Usage: node exporter.js <demo-path> [format]');
    console.log('  demo-path: Path to demo JSON (e.g., promotional/vim-master.json)');
    console.log('  format: "full" (1920x1080) or "shorts" (1080x1920)');
    process.exit(1);
  }

  const [demoPath, format = 'full'] = args;

  const exporter = new VideoExporter({
    demoPath,
    format,
    onProgress: (p) => console.log(`[${p.phase}] ${p.message}`)
  });

  exporter.export()
    .then(result => {
      console.log('\nExport complete!');
      console.log(`  Output: ${result.file}`);
      console.log(`  Frames: ${result.frames}`);
      console.log(`  Time: ${(result.duration / 1000).toFixed(1)}s`);
    })
    .catch(err => {
      console.error('Export failed:', err.message);
      process.exit(1);
    });
}
