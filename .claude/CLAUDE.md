# xSwarm Boss Project Instructions

## Versioning Policy

**MANDATORY**: Every time code is delivered for user testing, bump the version and reinstall.

### Version Format: MAJOR.MINOR.PATCH

- **MAJOR** (X.0.0): Large new features, breaking changes, significant refactors
- **MINOR** (0.X.0): Small features, enhancements, non-breaking additions
- **PATCH** (0.0.X): Bug fixes, print statement cleanup, minor tweaks

### Workflow

1. Make code changes
2. Bump version in `packages/assistant/pyproject.toml`
3. Reinstall: `python -m pip install -e packages/assistant`
4. Verify version: `python -c "from assistant import __version__; print(__version__)"`
5. Deliver to user for testing

### Version Location

- **Single source of truth**: `packages/assistant/pyproject.toml`
- `__version__` in `__init__.py` reads from package metadata automatically
- Never hardcode version in Python files

### Example

```bash
# After fixing bugs
# Edit pyproject.toml: version = "0.14.2"
python -m pip install -e packages/assistant
# Now user can test v0.14.2
```
