# Test Organization

Tests organized by component:

- **`assistant/`** - Assistant application tests (20 Python files)
- **`voice/`** - Moshi voice server tests (10 Python files)
- **`server/`** - Backend tests (9 Python + 11 JavaScript files)
- **`e2e/`** - End-to-end integration tests (1 Python file)

## Running Tests

```bash
# All Python tests
pytest tests/

# By component
pytest tests/assistant/
pytest tests/voice/
pytest tests/server/  # Python only
pytest tests/e2e/

# JavaScript server tests (Cloudflare Workers)
cd tests/server && node test-runner.js
```

## Support

- `fixtures/` - Test fixtures and data
- `utils/` - Test utilities
- `conftest.py` - Python shared fixtures
- `__snapshots__/` - UI snapshots
