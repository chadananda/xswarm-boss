# Test Utilities

Shared utilities for JavaScript tests.

## Contents

- `assert.js` - Custom assertion helpers
- `database.js` - Database test utilities
- `http.js` - HTTP request helpers
- `reporter.js` - Test reporting utilities
- `runner.js` - Test runner utilities

## Purpose

This directory contains reusable helper functions and utilities for JavaScript tests (primarily Cloudflare Workers tests in `tests/server/`).

## Usage

```javascript
const { assertEqual } = require('./utils/assert');
const { setupTestDb } = require('./utils/database');
const { makeRequest } = require('./utils/http');
```
