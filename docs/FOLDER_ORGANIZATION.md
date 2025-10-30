# xSwarm Project Folder Organization

This document describes the official folder organization for the xSwarm project.

## Organization Rules

### Root Directory
**Purpose:** Configuration files ONLY

**Allowed Files:**
- Configuration: `config.toml`, `.env`, `.env.example`, `wrangler.toml`
- Build configs: `Cargo.toml`, `package.json`, `pnpm-workspace.yaml`
- Git config: `.gitignore`, `.gitattributes`, `.lfsconfig`
- Essential docs: `README.md`, `CLAUDE.md`, `SECURITY.md`
- Scripts: `deploy.sh`, `justfile`

**NOT Allowed:**
- Implementation documentation
- Planning documents
- Test results
- Temporary files
- Any other .md files (except README, CLAUDE, SECURITY)

### planning/
**Purpose:** Architecture and planning documents

**Contents:**
- ARCHITECTURE.md - System architecture
- FEATURES.md - Feature specifications
- COMPLETE_SPECIFICATION.md - Full product specification
- SIMPLE_DESIGN.md - Design guidelines
- All technical planning documents
- API specifications
- Database schemas
- Integration guides

**Subdirectories:** None (flat structure for easy navigation)

### docs/
**Purpose:** User and developer documentation

**Structure:**
```
docs/
├── quickstart/          # Quick start guides
│   ├── QUICKSTART.md
│   ├── CLAUDE_CODE_QUICKSTART.md
│   └── QUICKSTART_STRIPE.md
├── deployment/          # Deployment documentation
│   ├── DEPLOYMENT.md
│   ├── DEPLOYMENT_CHECKLIST.md
│   ├── DEPLOYMENT_COMPLETE.md
│   └── DEPLOYMENT_SUMMARY.md
├── development/         # Development guides
├── sendgrid/           # SendGrid specific docs
├── IMPLEMENTATION_SUMMARY.md
├── DASHBOARD_IMPLEMENTATION.md
├── WEBSOCKET_INTEGRATION_SUMMARY.md
├── E2E_TESTS_README.md
├── AUTH_IMPLEMENTATION_COMPLETE.md
└── STRIPE_SETUP_COMPLETE.md
```

### tmp/
**Purpose:** Temporary files, test results, build artifacts

**Contents:**
- Test results
- Log files
- Build artifacts
- Temporary data
- Anything that can be safely deleted

**Note:** This directory can be added to `.gitignore`

## File Movement Guidelines

When adding new files to the project:

1. **Is it a config file?** → Root directory
2. **Is it planning/architecture?** → `planning/`
3. **Is it documentation?** → `docs/` (appropriate subdirectory)
4. **Is it temporary?** → `tmp/`

## Cross-References

When referencing files in documentation:

- Use relative paths from the current file location
- Update all references when moving files
- Check these common reference locations:
  - README.md
  - docs/**/*.md
  - planning/**/*.md

## Reorganization History

**Date:** October 29, 2025
**Changes:**
- Moved 15 documentation files from root to proper subdirectories
- Updated all cross-references
- Created `docs/quickstart/` and `docs/deployment/` subdirectories
- Moved test results to `tmp/`

**Files Moved:**
- 2 to `planning/`
- 3 to `docs/quickstart/`
- 6 to `docs/`
- 4 to `docs/deployment/`
- 4 to `tmp/`

See `tmp/reorganization-summary.txt` for complete details.

## Maintenance

To keep the project organized:

1. Regularly review root directory
2. Move any misplaced files to proper locations
3. Update cross-references when moving files
4. Clean `tmp/` directory periodically
5. Keep planning and docs directories well-structured

## Verification

To verify organization compliance:

```bash
# Check root directory only has config files
ls -1 | grep -E "\.md$" | grep -v -E "^(README|CLAUDE|SECURITY)\.md$"
# Should return nothing

# Check for unorganized files
find . -maxdepth 1 -name "*.md" -o -name "*.txt" -o -name "*.log"
# Should only show README.md, CLAUDE.md, SECURITY.md
```

## Questions?

If unsure where a file belongs, ask:
1. Is it config? → Root
2. Is it planning? → planning/
3. Is it docs? → docs/
4. Is it temporary? → tmp/
5. None of the above? → Create a new category in planning/ or docs/

---

**Last Updated:** October 29, 2025
**Maintained By:** xSwarm Development Team
