#!/bin/bash
# Omarchy Defender - Production Build Script
# Creates optimized build in /build directory

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
SRC_DIR="$PROJECT_ROOT/src"

echo "🛡️  Building Omarchy Defender..."
echo "   Source: $SRC_DIR"
echo "   Output: $BUILD_DIR"

# Clean build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy static files
echo "📦 Copying static files..."
cp "$SRC_DIR/manifest.json" "$BUILD_DIR/"
cp "$SRC_DIR/sw.js" "$BUILD_DIR/"

# Copy assets
echo "📦 Copying assets..."
cp -r "$SRC_DIR/assets" "$BUILD_DIR/"

# Process HTML - inline splash.css
echo "🔧 Processing HTML..."
SPLASH_CSS=$(cat "$SRC_DIR/splash.css")

# Read index.html and replace the splash.css link with inline styles
sed -e "/<link rel=\"stylesheet\" href=\"splash.css\">/r /dev/stdin" \
    -e "s|<link rel=\"stylesheet\" href=\"splash.css\">|<style>$SPLASH_CSS</style>|" \
    "$SRC_DIR/index.html" > "$BUILD_DIR/index.html" 2>/dev/null || \
    cp "$SRC_DIR/index.html" "$BUILD_DIR/index.html"

# Copy CSS and JS files (minification can be added later)
cp "$SRC_DIR/game.css" "$BUILD_DIR/"
cp "$SRC_DIR/splash.js" "$BUILD_DIR/"
cp "$SRC_DIR/game.js" "$BUILD_DIR/"
cp "$SRC_DIR/donation.js" "$BUILD_DIR/"

# Copy API routes for Cloudflare Pages
if [ -d "$PROJECT_ROOT/api" ]; then
  echo "📦 Copying API routes..."
  mkdir -p "$BUILD_DIR/api"
  cp "$PROJECT_ROOT/api/"*.js "$BUILD_DIR/api/"
fi

# Copy demo files
if [ -d "$PROJECT_ROOT/demos" ]; then
  echo "📦 Copying demo files..."
  cp -r "$PROJECT_ROOT/demos" "$BUILD_DIR/"
fi

# Create robots.txt
echo "🤖 Creating robots.txt..."
cat > "$BUILD_DIR/robots.txt" << 'EOF'
User-agent: *
Allow: /
Sitemap: https://xswarm.ai/omarchy-defender/sitemap.xml
EOF

# Create sitemap.xml
echo "🗺️  Creating sitemap.xml..."
cat > "$BUILD_DIR/sitemap.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://xswarm.ai/omarchy-defender/</loc>
    <lastmod>2024-12-04</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
EOF

# Calculate sizes
echo ""
echo "📊 Build Statistics:"
echo "   HTML:  $(wc -c < "$BUILD_DIR/index.html" | xargs) bytes"
echo "   CSS:   $(wc -c < "$BUILD_DIR/game.css" | xargs) bytes"
echo "   JS:    $(( $(wc -c < "$BUILD_DIR/game.js") + $(wc -c < "$BUILD_DIR/splash.js") + $(wc -c < "$BUILD_DIR/donation.js") )) bytes"
echo "   Total: $(du -sh "$BUILD_DIR" | cut -f1)"

echo ""
echo "✅ Build complete! Output in: $BUILD_DIR"
echo ""
echo "To preview locally:"
echo "   cd $BUILD_DIR && npx serve"
echo ""
echo "To deploy:"
echo "   ./scripts/deploy.sh"
