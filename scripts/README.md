# xSwarm Animation Scripts

Scripts for generating animated persona icons using AI.

## Animate Eye of Sauron

Creates a realistic animated fire loop for the Eye of Sauron persona icon.

The challenge: Getting fire to flow **outward from the center pupil** (not random motion).

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
   ```

3. **Get an API key** (see options below)

---

## Animation Options

Since controlling fire direction is challenging, we have multiple approaches:

### Option 1: Multi-Seed Attempt ⭐ Recommended

Generate **5 variations** with different random seeds, then pick the best one.

**Setup:**
```bash
# Already have Replicate? You're ready!
REPLICATE_API_KEY=r8_your_token_here  # Add to .env
```

**Run:**
```bash
pnpm animate:sauron:multi
```

**What happens:**
1. Generates 5 different animations (different random seeds)
2. Saves to `assets/sauron-variations/variation-1.mp4` through `variation-5.mp4`
3. Creates APNG and WebP for each
4. You preview all and pick the best

**Preview:**
```bash
open assets/sauron-variations/variation-1.mp4
open assets/sauron-variations/variation-2.mp4
# ... etc
```

**Use the winner:**
```bash
# Replace N with the best variation number
cp assets/sauron-variations/variation-N.webp packages/personas/sauron/icon.webp
cp assets/sauron-variations/variation-N.apng packages/personas/sauron/icon.apng
```

| **Pros** | **Cons** |
|----------|----------|
| ✅ Uses API you already have | ❌ No motion control (luck-based) |
| ✅ Multiple options to choose from | ❌ Takes 5x longer |
| ✅ Best chance of getting good result | |

**Cost:** ~$0.05-0.10 total | **Time:** 5-15 minutes

---

### Option 2: Luma AI Dream Machine (Text-Guided) ⭐ Best Quality

Official API with **text prompt control** and 1080p cinematic quality.

**Setup:**
```bash
# 1. Get API key: https://lumalabs.ai/dream-machine/api/keys
# 2. Add to .env
echo "LUMA_API_KEY=luma_your_key_here" >> .env
```

**Run:**
```bash
pnpm animate:sauron:luma
```

**What happens:**
1. Sends image + text prompt to Luma AI
2. Generates 1080p video with motion guided by prompt
3. Downloads and converts to APNG/WebP

**Text prompt used:**
> "Fire and flames radiating outward from the center pupil, dramatic orange fire flowing from the dark vertical slit, intense heat waves emanating outward in all directions"

| **Pros** | **Cons** |
|----------|----------|
| ✅ Text-guided motion control | ❌ Different service (new API key) |
| ✅ Official API, easy to get key | ❌ Slightly more expensive |
| ✅ 1080p cinematic quality | |
| ✅ Loop support built-in | |

**Cost:** ~$0.20-0.50 per generation | **Time:** 2-4 minutes

---

### Option 3: Runway Gen-2 (Text-Guided - Hard to Access)

**Best motion control** but API access is nearly impossible to get.

**Setup:**
```bash
# If you somehow get a Runway API key
echo "RUNWAY_API_KEY=your_key_here" >> .env
```

**Run:**
```bash
pnpm animate:sauron:runway
```

**Text prompt used:**
> "Fire and flames flowing outward from the center eye pupil, dramatic orange and yellow fire radiating from the dark vertical slit, intense heat waves emanating outward, cinematic fire effect"

| **Pros** | **Cons** |
|----------|----------|
| ✅ Text-guided motion control | ❌ API key almost impossible to obtain |
| ✅ Best directional control | ❌ Most expensive |
| ✅ Highest quality | |

**Cost:** ~$0.20 per 4-second clip | **Time:** 2-5 minutes

---

### Option 4: Single Attempt (Quick Test)

Quick single generation with Replicate (original script).

**Run:**
```bash
pnpm animate:sauron
```

**Good for:** Testing, quick iterations, when you get lucky on first try

---

## Output Formats

All scripts generate both formats:

| Format | Size | Compatibility | Recommended |
|--------|------|---------------|-------------|
| **APNG** | 6-11 MB | All browsers | Safest choice |
| **WebP** | 0.4-0.9 MB | Modern browsers | Smaller, use this |

### Using in SVG

After generating, the icon is already embedded in `packages/personas/sauron/icon.svg`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg width="256" height="256" viewBox="0 0 256 256">
  <title>Eye of Sauron</title>

  <!-- AI-generated animated fire loop -->
  <image href="icon.webp" width="256" height="256"/>
</svg>
```

---

## Tips for Best Results

### What to Look For

When previewing variations, look for:
- ✅ **Fire flowing outward** from center pupil
- ✅ **Consistent sharpness** (no blur cycling)
- ✅ **Smooth loop** (start matches end)
- ✅ **Realistic fire** (organic movement)

### If Nothing Works

Try adjusting parameters in the script:

```javascript
// scripts/animate-sauron.js or scripts/animate-sauron-multi-try.js

motion_bucket_id: 127,  // 1-255 (higher = more motion)
cond_aug: 0.02,         // 0-1 (higher = more variation)
frames_per_second: 8,   // 3-30 (speed)
seed: 42,              // Any number (controls randomness)
```

---

## Troubleshooting

**"API key not found"**
```bash
# Make sure it's in .env file
cat .env | grep API_KEY
```

**"FFmpeg not found"**
```bash
brew install ffmpeg  # macOS
```

**"Animation goes from sharp to blurry"**
- Lower `cond_aug` to 0.005 or 0.01
- Try multi-seed option to find consistent one

**"Fire moves randomly, not outward"**
- Try multi-seed option (5 chances)
- Or use Leonardo/Runway if available

**"File too large"**
- Use WebP instead of APNG
- Reduce frames: `video_length: "14_frames_with_svd"`

---

## Cost Summary

| Service | Per Generation | Best For |
|---------|----------------|----------|
| **Replicate** | $0.01-0.02 | Single attempts |
| **Replicate (5x)** | $0.05-0.10 | Multiple options |
| **Luma AI** | $0.20-0.50 | Text-guided, best quality |
| **Runway** | $0.20 | Text-guided (API inaccessible) |
| **Leonardo** | $0.01-0.03 | (Site broken) |

---

## Other Personas

To animate other persona icons:

1. **Copy multi-try script:**
   ```bash
   cp scripts/animate-sauron-multi-try.js scripts/animate-[persona]-multi-try.js
   ```

2. **Update paths:**
   ```javascript
   const INPUT_IMAGE = path.join(__dirname, '../assets/[persona].jpg');
   const OUTPUT_DIR = path.join(__dirname, '../assets/[persona]-variations');
   ```

3. **Add to package.json:**
   ```json
   "animate:[persona]": "node scripts/animate-[persona]-multi-try.js"
   ```

4. **Run:**
   ```bash
   pnpm animate:[persona]
   ```

---

## Recommended Workflow

For best results with minimal cost:

1. **Start with multi-seed** (`pnpm animate:sauron:multi`)
   - Cost: ~$0.05-0.10 for 5 variations
   - Uses Replicate API you already have

2. **Preview all 5 variations**
   - Look for fire flowing outward from center
   - Check for consistent sharpness

3. **If one is good** → Use it! Copy to packages/personas/sauron/

4. **If none are good** → Try Luma AI for text-guided control
   - Cost: ~$0.20-0.50 per attempt
   - Text prompt guides fire direction
   - 1080p cinematic quality
   - Run: `pnpm animate:sauron:luma`

5. **If still no luck** → Adjust parameters in multi-seed and retry

This strategy gives you 5 chances for under $0.10, with a high-quality fallback option.
