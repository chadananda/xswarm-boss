#!/usr/bin/env python3
"""
Voice Training Script for xSwarm Personas

Downloads audio from URLs in a persona's audio/SOURCES.md file,
converts to WAV 24kHz format suitable for MOSHI voice training.

Usage:
    python scripts/train_voice.py --persona hal-9000
    python scripts/train_voice.py --persona jarvis --limit 5
    python scripts/train_voice.py --all

Requirements:
    pip install yt-dlp requests pyyaml

System dependencies:
    ffmpeg (for audio conversion)
    yt-dlp (for YouTube downloads)
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
import requests

# Persona base path
PERSONAS_DIR = Path("packages/personas")

def parse_sources_md(sources_file):
    """Extract URLs from a SOURCES.md file."""
    if not sources_file.exists():
        print(f"❌ Sources file not found: {sources_file}")
        return []

    urls = []
    with open(sources_file, 'r') as f:
        content = f.read()

        # Find URLs in markdown (both bare URLs and markdown links)
        # Match http:// or https:// URLs
        url_pattern = r'https?://[^\s\)>]+'
        found_urls = re.findall(url_pattern, content)

        for url in found_urls:
            # Skip documentation/reference URLs
            if any(skip in url.lower() for skip in ['reddit.com/r/', 'goodreads.com', 'martinhill.me.uk']):
                # These are quote collections, not audio sources
                continue
            urls.append(url)

    return urls

def is_youtube_url(url):
    """Check if URL is from YouTube."""
    return 'youtube.com' in url or 'youtu.be' in url

def download_youtube(url, output_path, clip_num):
    """Download audio from YouTube using yt-dlp."""
    try:
        output_file = output_path / f"{clip_num:02d}_source.wav"

        print(f"  📥 Downloading from YouTube: {url}")

        cmd = [
            'yt-dlp',
            '-x',  # Extract audio
            '--audio-format', 'wav',
            '--audio-quality', '0',  # Best quality
            '--postprocessor-args', 'ffmpeg:-ar 24000 -ac 1',  # 24kHz mono
            '-o', str(output_file.with_suffix('.%(ext)s')),
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"  ✅ Downloaded: {output_file.name}")
            return True
        else:
            print(f"  ❌ Failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"  ❌ Error downloading: {e}")
        return False

def download_direct_audio(url, output_path, clip_num):
    """Download direct audio file (MP3, WAV, etc.) and convert."""
    try:
        output_file = output_path / f"{clip_num:02d}_source.wav"
        temp_file = output_path / f"temp_{clip_num:02d}"

        print(f"  📥 Downloading: {url}")

        # Download file
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        # Save to temp file
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Convert to WAV 24kHz using ffmpeg
        cmd = [
            'ffmpeg',
            '-i', str(temp_file),
            '-acodec', 'pcm_s16le',
            '-ar', '24000',
            '-ac', '1',  # Mono
            '-y',  # Overwrite
            str(output_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Clean up temp file
        temp_file.unlink()

        if result.returncode == 0:
            print(f"  ✅ Converted: {output_file.name}")
            return True
        else:
            print(f"  ❌ Conversion failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def download_from_soundboard(url, output_path, clip_num):
    """Handle soundboard sites (requires manual download for now)."""
    print(f"  ⚠️  Soundboard URL detected: {url}")
    print(f"     → Please visit this site and manually download clips")
    print(f"     → Save files to: {output_path}")
    print(f"     → Use naming: {clip_num:02d}_greeting.wav, etc.")
    return False

def train_persona(persona_name, limit=None, skip_existing=True):
    """Download and convert audio for a specific persona."""
    persona_path = PERSONAS_DIR / persona_name
    sources_file = persona_path / "audio" / "SOURCES.md"
    output_path = persona_path / "audio" / "samples"

    if not persona_path.exists():
        print(f"❌ Persona not found: {persona_name}")
        return False

    if not sources_file.exists():
        print(f"❌ No SOURCES.md found for persona: {persona_name}")
        return False

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Parse URLs from SOURCES.md
    urls = parse_sources_md(sources_file)

    if not urls:
        print(f"⚠️  No audio URLs found in {sources_file}")
        return False

    print(f"\n🎤 Training voice for persona: {persona_name}")
    print(f"   Found {len(urls)} source URLs")

    if limit:
        urls = urls[:limit]
        print(f"   Limiting to first {limit} URLs")

    print(f"   Output: {output_path}\n")

    # Download and convert each URL
    successful = 0
    clip_num = 1

    for url in urls:
        print(f"\n[{clip_num}/{len(urls)}] Processing: {url[:60]}...")

        # Check if already exists
        existing_file = output_path / f"{clip_num:02d}_source.wav"
        if skip_existing and existing_file.exists():
            print(f"  ⏭️  Skipping (already exists): {existing_file.name}")
            clip_num += 1
            continue

        # Determine download method
        if is_youtube_url(url):
            if download_youtube(url, output_path, clip_num):
                successful += 1
        elif any(sb in url for sb in ['101soundboards.com', 'myinstants.com', 'soundboard']):
            download_from_soundboard(url, output_path, clip_num)
        else:
            # Try direct download
            if download_direct_audio(url, output_path, clip_num):
                successful += 1

        clip_num += 1

    print(f"\n✨ Training complete for {persona_name}!")
    print(f"   Successfully downloaded: {successful}/{len(urls)} clips")
    print(f"   Saved to: {output_path}")

    if successful > 0:
        print(f"\n📝 Next steps:")
        print(f"   1. Listen to clips and rename descriptively (e.g., 01_greeting.wav)")
        print(f"   2. Edit in Audacity if needed (remove silence, normalize)")
        print(f"   3. Run: xswarm voice train --persona {persona_name}")

    return successful > 0

def train_all_personas(limit=None):
    """Train voices for all available personas."""
    personas = [d.name for d in PERSONAS_DIR.iterdir() if d.is_dir() and (d / "audio" / "SOURCES.md").exists()]

    print(f"🎤 Training voices for {len(personas)} personas\n")

    for persona in sorted(personas):
        train_persona(persona, limit=limit)
        print("\n" + "="*60 + "\n")

def check_dependencies():
    """Check if required tools are installed."""
    missing = []

    # Check ffmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing.append('ffmpeg')

    # Check yt-dlp
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing.append('yt-dlp')

    if missing:
        print("❌ Missing required dependencies:")
        for tool in missing:
            print(f"   - {tool}")
        print("\nInstall with:")
        print("   macOS:      brew install ffmpeg yt-dlp")
        print("   Arch Linux: sudo pacman -S ffmpeg yt-dlp")
        print("   Other:      pip install yt-dlp (+ install ffmpeg)")
        return False

    return True

def main():
    parser = argparse.ArgumentParser(
        description='Download and convert audio for xSwarm persona voice training'
    )
    parser.add_argument('--persona', type=str, help='Persona name (e.g., hal-9000)')
    parser.add_argument('--all', action='store_true', help='Train all personas')
    parser.add_argument('--limit', type=int, help='Limit number of clips to download')
    parser.add_argument('--force', action='store_true', help='Re-download existing files')

    args = parser.parse_args()

    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)

    # Determine what to train
    if args.all:
        train_all_personas(limit=args.limit)
    elif args.persona:
        train_persona(args.persona, limit=args.limit, skip_existing=not args.force)
    else:
        parser.print_help()
        print("\n💡 Examples:")
        print("   python scripts/train_voice.py --persona hal-9000")
        print("   python scripts/train_voice.py --persona jarvis --limit 3")
        print("   python scripts/train_voice.py --all")

if __name__ == '__main__':
    main()
