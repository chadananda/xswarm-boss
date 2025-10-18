#!/usr/bin/env python3
"""
Animated Header Generator for xSwarm

Creates a rotating animated banner featuring all persona icons with glitch
transitions between them. Perfect for README headers and promotional material.

Requirements:
    pip install pillow requests numpy

Usage:
    python scripts/create_animated_header.py
    python scripts/create_animated_header.py --output assets/header.gif
    python scripts/create_animated_header.py --fps 10 --glitch-frames 3
"""

import argparse
import io
import os
import random
import sys
from pathlib import Path
from urllib.request import urlopen

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import numpy as np
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("   pip install pillow numpy")
    sys.exit(1)

# Persona icon URLs (best animated GIFs from our collections)
PERSONA_ICONS = {
    'hal-9000': 'https://media.giphy.com/media/l0HlNyrvLKBMxjFzG/giphy.gif',
    'kitt': 'https://media.tenor.com/QVPOKZDrWb4AAAAC/knight-rider-scanner.gif',
    'cylon': 'https://media.giphy.com/media/xT9DPCKNlqT6RznP9K/giphy.gif',
    'c3po': 'https://media.giphy.com/media/3o7TKS6AWINqbg3FV6/giphy.gif',
    'glados': 'https://media.giphy.com/media/8vtm3YCdxtUvjTn0U3/giphy.gif',
    'tars': 'https://media.giphy.com/media/3o7aCTPPm4OHfRLSH6/giphy.gif',
    'marvin': 'https://media.giphy.com/media/l0HlN5Y28D9MzzcRy/giphy.gif',
    'sauron': 'https://media.giphy.com/media/njYrp176NQsHS/giphy.gif',
    'jarvis': 'https://media.giphy.com/media/3o7aCTPPm4OHfRLSH6/giphy.gif',
    'dalek': 'https://media.giphy.com/media/xT9DPCKNlqT6RznP9K/giphy.gif',
}

# Persona colors (from persona configs)
PERSONA_COLORS = {
    'hal-9000': '#DC143C',
    'kitt': '#FF0000',
    'cylon': '#FF0000',
    'c3po': '#FFD700',
    'glados': '#FFA500',
    'tars': '#4A4A4A',
    'marvin': '#708090',
    'sauron': '#FF4500',
    'jarvis': '#00A3E0',
    'dalek': '#8B0000',
}

def create_glitch_frame(img, intensity=0.5):
    """Apply glitch effect to an image"""
    arr = np.array(img)
    h, w = arr.shape[:2]

    # RGB channel shift
    shift = int(w * 0.02 * intensity)
    glitched = arr.copy()

    if len(arr.shape) == 3:  # Color image
        # Red channel shift
        glitched[:, shift:, 0] = arr[:, :-shift, 0]
        # Blue channel shift opposite direction
        glitched[:, :-shift, 2] = arr[:, shift:, 2]

    # Random horizontal line displacements
    num_glitches = int(10 * intensity)
    for _ in range(num_glitches):
        y = random.randint(0, h - 1)
        height = random.randint(2, 10)
        displacement = random.randint(-20, 20)

        if y + height < h:
            glitched[y:y+height] = np.roll(glitched[y:y+height], displacement, axis=1)

    return Image.fromarray(glitched)

def create_text_overlay(size, text, color):
    """Create text overlay for persona name"""
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        # Try to use a nice font
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
    except:
        font = ImageFont.load_default()

    # Get text size
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Center text
    x = (size[0] - text_width) // 2
    y = size[1] - text_height - 20

    # Draw text with shadow
    draw.text((x+2, y+2), text, fill=(0, 0, 0, 180), font=font)
    draw.text((x, y), text, fill=color + (255,), font=font)

    return img

def download_and_resize(url, size=(800, 400)):
    """Download image and resize to target size"""
    try:
        with urlopen(url) as response:
            img_data = response.read()

        img = Image.open(io.BytesIO(img_data))

        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize maintaining aspect ratio
        img.thumbnail(size, Image.Resampling.LANCZOS)

        # Center on canvas
        canvas = Image.new('RGB', size, (0, 0, 0))
        offset = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
        canvas.paste(img, offset)

        return canvas
    except Exception as e:
        print(f"⚠️  Failed to download {url}: {e}")
        # Return placeholder
        img = Image.new('RGB', size, (20, 20, 20))
        draw = ImageDraw.Draw(img)
        draw.text((size[0]//2-50, size[1]//2), "ICON", fill=(100, 100, 100))
        return img

def create_animated_header(output_path='assets/xswarm-header.gif',
                          size=(800, 400),
                          icon_duration=2000,
                          glitch_frames=3,
                          fps=15):
    """
    Create animated header with rotating persona icons and glitch transitions.

    Args:
        output_path: Where to save the animated GIF
        size: Output size (width, height)
        icon_duration: How long to show each icon (ms)
        glitch_frames: Number of glitch transition frames
        fps: Frames per second
    """

    print("🎬 Creating animated xSwarm header...")
    print(f"   Output: {output_path}")
    print(f"   Size: {size[0]}x{size[1]}")
    print(f"   {len(PERSONA_ICONS)} personas\n")

    frames = []
    frame_duration = 1000 // fps  # ms per frame
    icon_frames = (icon_duration // frame_duration) - glitch_frames

    for name, url in PERSONA_ICONS.items():
        print(f"📥 Processing {name}...")

        # Download and resize icon
        icon = download_and_resize(url, size)

        # Add persona name overlay
        color_hex = PERSONA_COLORS.get(name, '#FFFFFF')
        color_rgb = tuple(int(color_hex[i:i+2], 16) for i in (1, 3, 5))
        text_overlay = create_text_overlay(size, name.upper(), color_rgb)

        # Composite
        icon_with_text = icon.copy()
        icon_with_text.paste(text_overlay, (0, 0), text_overlay)

        # Add normal frames
        for _ in range(icon_frames):
            frames.append(icon_with_text.copy())

        # Add glitch transition frames
        print(f"✨ Adding glitch transition...")
        for i in range(glitch_frames):
            intensity = (i + 1) / glitch_frames
            glitch = create_glitch_frame(icon_with_text, intensity)
            frames.append(glitch)

    # Save animated GIF
    print(f"\n💾 Saving animation ({len(frames)} frames)...")
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=frame_duration,
        loop=0,
        optimize=False
    )

    file_size = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"\n✅ Done! Created {output_path}")
    print(f"   Size: {file_size:.2f} MB")
    print(f"   Frames: {len(frames)}")
    print(f"   Duration: {len(frames) * frame_duration / 1000:.1f}s")

    return output_path

def main():
    parser = argparse.ArgumentParser(
        description='Create animated xSwarm header with rotating persona icons'
    )
    parser.add_argument(
        '--output', '-o',
        default='assets/xswarm-header.gif',
        help='Output file path (default: assets/xswarm-header.gif)'
    )
    parser.add_argument(
        '--size',
        default='800x400',
        help='Output size in WIDTHxHEIGHT (default: 800x400)'
    )
    parser.add_argument(
        '--icon-duration',
        type=int,
        default=2000,
        help='Duration to show each icon in ms (default: 2000)'
    )
    parser.add_argument(
        '--glitch-frames',
        type=int,
        default=3,
        help='Number of glitch transition frames (default: 3)'
    )
    parser.add_argument(
        '--fps',
        type=int,
        default=15,
        help='Frames per second (default: 15)'
    )

    args = parser.parse_args()

    # Parse size
    width, height = map(int, args.size.split('x'))
    size = (width, height)

    # Create animation
    create_animated_header(
        output_path=args.output,
        size=size,
        icon_duration=args.icon_duration,
        glitch_frames=args.glitch_frames,
        fps=args.fps
    )

if __name__ == '__main__':
    main()
