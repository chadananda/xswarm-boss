# Documentation Archive

This directory contains **archived documentation** from previous phases of the xSwarm-Boss project. These files are preserved for historical reference but are no longer actively maintained.

## Why Archive?

Documentation is archived when it:
- References obsolete implementations (e.g., Rust → Python migration)
- Documents completed debugging investigations
- Contains historical development session logs
- Is superseded by newer, consolidated documentation

## Archive Structure

### `rust-legacy/`
Legacy documentation from the **Rust implementation** (Q4 2025):
- MOSHI audio system debugging files
- Rust-specific architecture and build documentation
- Performance testing (CPU vs Metal)
- Status files referencing Rust codebase

**Why Archived**: Project migrated from Rust to Python (Textual TUI) in November 2025 for faster iteration and better AI integration.

### `moshi-rust-debugging/`
Extensive **MOSHI audio debugging investigation** (29 files):
- Codec debugging traces
- Tensor shape analysis
- Audio pipeline investigations
- Multiple fix attempts (v7.3 - v7.6)

**Why Archived**: Debugging sessions for Rust implementation of MOSHI audio system. Issue resolved during Python migration.

### `sessions/`
**Development session summaries** from various implementation phases:
- Session logs with timestamps
- Phase completion summaries
- Implementation progress tracking

**Why Archived**: Historical development logs. Current status tracked in `/docs/STATUS.md`.

### `implementation-summaries/`
**Feature implementation summaries** (old format):
- Individual implementation completion reports
- Feature-specific documentation

**Why Archived**: Consolidated into `/docs/implementation/CHANGELOG.md` for easier navigation.

## Accessing Archived Documentation

All files in this archive are preserved with full git history. To view the history of any archived file:

```bash
# View file history (works even after archiving with git mv)
git log --follow -- docs/archive/rust-legacy/FILENAME.md

# View file contents at specific commit
git show COMMIT_HASH:docs/FILENAME.md
```

## When to Use Archived Docs

Archived documentation may be useful for:
- Understanding historical design decisions
- Debugging similar issues in the future
- Reference for migrating related systems
- Academic interest in the development process

**For current documentation, see [`/docs/README.md`](../README.md)**

---

**Archive Created**: 2025-11-12
**Last Updated**: 2025-11-12
