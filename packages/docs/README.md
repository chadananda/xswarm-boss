# xSwarm-boss Documentation

This directory contains the xSwarm-boss documentation website built with [Astro](https://astro.build) and [Starlight](https://starlight.astro.build).

## Development

```bash
# Install dependencies
pnpm install

# Start dev server
pnpm dev

# Build for production
pnpm build

# Preview production build
pnpm preview
```

## Structure

```
docs/
├── src/
│   ├── content/
│   │   └── docs/          # Markdown documentation
│   ├── styles/
│   │   └── custom.css     # Custom styles
│   └── assets/            # Images, logos
├── public/
│   ├── downloads/         # Build artifacts
│   └── assets/            # Static assets
├── astro.config.mjs       # Astro configuration
└── package.json
```

## Adding Documentation

1. Create `.md` or `.mdx` files in `src/content/docs/`
2. Add frontmatter:
```yaml
---
title: Page Title
description: Page description
---
```
3. Update sidebar in `astro.config.mjs`

## Deployment

The site is automatically deployed to GitHub Pages via GitHub Actions on push to main.

Manual deployment:
```bash
pnpm build
# Upload dist/ to hosting
```

## Learn More

- [Astro Documentation](https://docs.astro.build)
- [Starlight Documentation](https://starlight.astro.build)
