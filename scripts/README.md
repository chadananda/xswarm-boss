# xSwarm Animation Scripts

Scripts for generating animated persona icons using AI.

## Animate Eye of Sauron

Creates a realistic animated fire loop for the Eye of Sauron persona icon.

### Prerequisites

1. **Install dependencies:**
   ```bash
   pnpm install
   ```

2. **Install FFmpeg:**
   ```bash
   # macOS
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt-get install ffmpeg

   # Arch Linux
   sudo pacman -S ffmpeg
   ```

3. **Get Replicate API token:**
   - Sign up at https://replicate.com
   - Go to https://replicate.com/account/api-tokens
   - Create a new API token
   - Add to `.env` file:
     ```bash
     REPLICATE_API_TOKEN=r8_your_token_here
     ```

### Usage

```bash
# Run the animation script
pnpm animate:sauron
```

### What it does

1. **Uploads** `assets/sauron.jpg` to Replicate
2. **Generates** animated video using Stable Video Diffusion AI
   - Creates 14-frame loop (~2.3 seconds at 6 fps)
   - Optimized for fire/flame movement
   - Preserves image quality
3. **Downloads** the video to `assets/sauron-animated.mp4`
4. **Converts** to formats:
   - `packages/personas/sauron/icon.apng` - Animated PNG with transparency
   - `packages/personas/sauron/icon.webp` - Smaller WebP format

### Cost

Using Replicate API with Stable Video Diffusion:
- **~$0.01-0.02** per generation
- Fast (usually 1-3 minutes)

### Output Formats

| Format | Transparency | Size | Use Case |
|--------|--------------|------|----------|
| **APNG** | ✅ Yes | 1-3 MB | Best for SVG embedding |
| **WebP** | ✅ Yes | 0.5-1 MB | Smaller, modern browsers |
| **MP4** | ❌ No | Smallest | Preview only |

### Using in SVG

After generating, update `packages/personas/sauron/icon.svg`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg width="256" height="256" viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
  <title>Eye of Sauron</title>

  <!-- Embedded animated image -->
  <image href="icon.apng" width="256" height="256"/>

  <!-- Or use WebP for smaller size -->
  <!-- <image href="icon.webp" width="256" height="256"/> -->
</svg>
```

### Troubleshooting

**"REPLICATE_API_TOKEN not found"**
- Make sure you've added the token to `.env`
- Load it: `source .env` or restart your terminal

**"FFmpeg not found"**
- Install FFmpeg (see Prerequisites above)

**"APNG is large (>2 MB)"**
- Use the WebP version instead (icon.webp)
- Or reduce frames: edit `video_length: "14_frames_with_svd"` to fewer frames

**Animation looks wrong**
- Adjust motion settings in the script:
  - `motion_bucket_id`: 127 (default), lower = less motion, higher = more motion
  - `frames_per_second`: 6 (default), adjust for speed
  - `cond_aug`: 0.02 (default), higher = more variation

### Advanced: Custom Settings

Edit `scripts/animate-sauron.js` to adjust:

```javascript
{
  video_length: "14_frames_with_svd", // 14 or 25 frames
  frames_per_second: 6,                // 3-30 fps
  motion_bucket_id: 127,               // 1-255 (motion amount)
  cond_aug: 0.02,                      // 0-1 (variation)
}
```

## Other Personas

To create animations for other personas:

1. **Copy the script:**
   ```bash
   cp scripts/animate-sauron.js scripts/animate-[persona].js
   ```

2. **Update paths** in the new script:
   ```javascript
   const INPUT_IMAGE = path.join(__dirname, '../assets/[persona].jpg');
   const OUTPUT_APNG = path.join(__dirname, '../packages/personas/[persona]/icon.apng');
   ```

3. **Add to package.json:**
   ```json
   "animate:[persona]": "node scripts/animate-[persona].js"
   ```

4. **Run:**
   ```bash
   pnpm animate:[persona]
   ```

## Cost Optimization

To minimize API costs:

1. **Test with static first** - Make sure the base image looks good
2. **Use short loops** - 14 frames is usually enough for smooth loops
3. **Batch multiple generations** - The API has volume discounts
4. **Cache results** - Save generated videos, don't regenerate unnecessarily

## Alternative APIs

If you prefer different AI services:

### Runway ML
- Higher quality
- More expensive (~$0.05/second)
- Better for complex motion

### Pika Labs
- Good quality
- Similar pricing to Replicate
- Different motion style

### Local (Free)
- Use AnimateDiff or SVD locally
- Requires GPU (8GB+ VRAM)
- No API costs but slower

Update the script to use a different API by changing the `replicate.run()` call.
