# Server Tests

This directory contains tests for the **server-side components** including conversation logic, AI clients, tools, and integrations.

## Test Files

- `test_ai_client.py` - Tests for AI client (Anthropic/OpenAI)
- `test_conversation_loop.py` - Tests for conversation state management
- `test_conversation_edge_cases.py` - Edge case tests for conversation handling
- `test_tool_calling.py` - Tests for tool execution and calling
- `test_persona_switching.py` - Tests for persona switching functionality
- `test_phone_integration.py` - Tests for Twilio phone integration
- `test_integration.py` - General integration tests

## Running Tests

```bash
# Run all server tests
pytest packages/assistant/tests/server/

# Run specific test file
pytest packages/assistant/tests/server/test_conversation_loop.py -v
```
