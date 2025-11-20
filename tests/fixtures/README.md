# Test Fixtures

Test data and fixtures for all test categories.

## Contents

- `users.json` - Sample user data for testing

## Purpose

This directory contains static test data, mock responses, and fixture files used across all test categories. Fixtures should be:
- **Static** - Not generated at runtime
- **Reusable** - Used by multiple tests
- **Realistic** - Representative of production data

## Usage

```python
import json
from pathlib import Path

# Load fixture
fixtures_dir = Path(__file__).parent.parent / "fixtures"
users = json.loads((fixtures_dir / "users.json").read_text())
```
