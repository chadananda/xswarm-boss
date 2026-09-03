/**
 * Generate DEFENDER logo matching Omarchy pixel style
 * Uses canvas to create pixel art text in red
 */

const { createCanvas } = require('canvas');
const fs = require('fs');
const path = require('path');

// Pixel font definition for DEFENDER letters (8x8 grid per character)
// Each letter is defined as an array of rows, where 1 = filled pixel
const pixelFont = {
  D: [
    [1,1,1,1,1,1,0,0],
    [1,1,0,0,0,1,1,0],
    [1,1,0,0,0,0,1,1],
    [1,1,0,0,0,0,1,1],
    [1,1,0,0,0,0,1,1],
    [1,1,0,0,0,0,1,1],
    [1,1,0,0,0,1,1,0],
    [1,1,1,1,1,1,0,0]
  ],
  E: [
    [1,1,1,1,1,1,1,1],
    [1,1,0,0,0,0,0,0],
    [1,1,0,0,0,0,0,0],
    [1,1,1,1,1,1,0,0],
    [1,1,0,0,0,0,0,0],
    [1,1,0,0,0,0,0,0],
    [1,1,0,0,0,0,0,0],
    [1,1,1,1,1,1,1,1]
  ],
  F: [
    [1,1,1,1,1,1,1,1],
    [1,1,0,0,0,0,0,0],
    [1,1,0,0,0,0,0,0],
    [1,1,1,1,1,1,0,0],
    [1,1,0,0,0,0,0,0],
    [1,1,0,0,0,0,0,0],
    [1,1,0,0,0,0,0,0],
    [1,1,0,0,0,0,0,0]
  ],
  N: [
    [1,1,0,0,0,0,1,1],
    [1,1,1,0,0,0,1,1],
    [1,1,1,1,0,0,1,1],
    [1,1,0,1,1,0,1,1],
    [1,1,0,0,1,1,1,1],
    [1,1,0,0,0,1,1,1],
    [1,1,0,0,0,0,1,1],
    [1,1,0,0,0,0,1,1]
  ],
  R: [
    [1,1,1,1,1,1,0,0],
    [1,1,0,0,0,1,1,0],
    [1,1,0,0,0,1,1,0],
    [1,1,1,1,1,1,0,0],
    [1,1,0,1,1,0,0,0],
    [1,1,0,0,1,1,0,0],
    [1,1,0,0,0,1,1,0],
    [1,1,0,0,0,0,1,1]
  ]
};

function generateDefenderLogo() {
  const text = 'DEFENDER';
  const pixelSize = 8;  // Size of each "pixel" block
  const charWidth = 8;  // Grid width per character
  const charHeight = 8; // Grid height per character
  const spacing = 2;    // Pixels between characters

  const totalWidth = text.length * (charWidth * pixelSize) + (text.length - 1) * (spacing * pixelSize);
  const totalHeight = charHeight * pixelSize;

  // Add padding
  const padding = pixelSize * 2;
  const canvasWidth = totalWidth + padding * 2;
  const canvasHeight = totalHeight + padding * 2;

  const canvas = createCanvas(canvasWidth, canvasHeight);
  const ctx = canvas.getContext('2d');

  // Transparent background
  ctx.clearRect(0, 0, canvasWidth, canvasHeight);

  // Red color matching the CSS
  const red = '#ff3333';

  let xOffset = padding;

  for (const char of text) {
    const charData = pixelFont[char];
    if (charData) {
      ctx.fillStyle = red;

      for (let row = 0; row < charHeight; row++) {
        for (let col = 0; col < charWidth; col++) {
          if (charData[row][col] === 1) {
            ctx.fillRect(
              xOffset + col * pixelSize,
              padding + row * pixelSize,
              pixelSize,
              pixelSize
            );
          }
        }
      }
    }
    xOffset += (charWidth + spacing) * pixelSize;
  }

  // Save the image
  const outputPath = path.join(__dirname, '../src/assets/images/defender-logo.png');
  const buffer = canvas.toBuffer('image/png');
  fs.writeFileSync(outputPath, buffer);

  console.log(`Generated: ${outputPath}`);
  console.log(`Dimensions: ${canvasWidth}x${canvasHeight}`);
}

generateDefenderLogo();
