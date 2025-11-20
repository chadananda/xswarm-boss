# E2E Tests

End-to-end integration tests for the voice assistant.

## Test Files (1)

- `test_dashboard_e2e.py` - Dashboard E2E tests using Textual Pilot
  - Tests reactive state changes
  - Tests tab navigation
  - Tests UI updates
  - Mocks heavy dependencies for headless testing

## Running

```bash
# All E2E tests
pytest tests/e2e/

# Specific test
pytest tests/e2e/test_dashboard_e2e.py -v
```

## Approach

E2E tests use Textual's Pilot to simulate user interactions and verify the complete application flow without requiring hardware initialization.
