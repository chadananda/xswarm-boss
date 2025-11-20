"""
Unit tests for persona switching functionality.

Tests cover:
- PersonaSwitchTool creation and execution
- AI function calling integration
- Tool registry management
- Callback invocation
- Error handling
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from assistant.tools.persona_tool import (
    create_persona_switch_tool,
    switch_persona_handler,
    get_persona_switching_system_prompt
)
from assistant.tools.registry import ToolRegistry
from assistant.personas.manager import PersonaManager


@pytest.fixture
def mock_persona_manager():
    """Create mock persona manager with test personas."""
    manager = Mock(spec=PersonaManager)
    manager.list_personas.return_value = ["JARVIS", "GLaDOS", "Samantha", "HAL9000"]

    # Create mock personas
    jarvis = Mock()
    jarvis.name = "JARVIS"
    jarvis.display_name = "J.A.R.V.I.S."
    jarvis.theme_color = "#00D4FF"
    jarvis.description = "Just A Rather Very Intelligent System"

    glados = Mock()
    glados.name = "GLaDOS"
    glados.display_name = "GLaDOS"
    glados.theme_color = "#FFA500"
    glados.description = "Genetic Lifeform and Disk Operating System"

    manager.get_persona.side_effect = lambda name: {
        "JARVIS": jarvis,
        "GLaDOS": glados
    }.get(name)

    return manager, jarvis, glados


@pytest.mark.asyncio
async def test_persona_switch_tool_creation(mock_persona_manager):
    """Test creating persona switch tool."""
    manager, _, _ = mock_persona_manager

    tool = create_persona_switch_tool(manager)

    assert tool.name == "switch_persona"
    assert len(tool.parameters) == 1
    assert tool.parameters[0].name == "persona_name"
    assert tool.parameters[0].required == True
    assert tool.parameters[0].enum == ["JARVIS", "GLaDOS", "Samantha", "HAL9000"]


@pytest.mark.asyncio
async def test_successful_persona_switch(mock_persona_manager):
    """Test successful persona switching."""
    manager, jarvis, glados = mock_persona_manager
    manager.set_current_persona.return_value = True
    manager.get_current_persona.side_effect = [jarvis, glados]

    result = await switch_persona_handler("GLaDOS", manager)

    assert result["success"] == True
    assert result["persona"]["name"] == "GLaDOS"
    assert result["persona"]["display_name"] == "GLaDOS"
    assert result["persona"]["theme_color"] == "#FFA500"
    assert result["previous_persona"] == "JARVIS"
    assert "Switched to" in result["message"]


@pytest.mark.asyncio
async def test_failed_persona_switch(mock_persona_manager):
    """Test persona switch with invalid name."""
    manager, jarvis, _ = mock_persona_manager
    manager.set_current_persona.return_value = False
    manager.get_current_persona.return_value = jarvis

    result = await switch_persona_handler("InvalidPersona", manager)

    assert result["success"] == False
    assert "not found" in result["error"]
    assert "available_personas" in result
    assert result["available_personas"] == ["JARVIS", "GLaDOS", "Samantha", "HAL9000"]


@pytest.mark.asyncio
async def test_persona_switch_with_callback(mock_persona_manager):
    """Test persona switch invokes callback."""
    manager, jarvis, glados = mock_persona_manager
    manager.set_current_persona.return_value = True
    manager.get_current_persona.side_effect = [jarvis, glados]

    callback_invoked = False
    old_received = None
    new_received = None

    async def test_callback(old, new):
        nonlocal callback_invoked, old_received, new_received
        callback_invoked = True
        old_received = old
        new_received = new

    result = await switch_persona_handler("GLaDOS", manager, test_callback)

    assert result["success"] == True
    assert callback_invoked == True
    assert old_received.name == "JARVIS"
    assert new_received.name == "GLaDOS"


@pytest.mark.asyncio
async def test_persona_switch_callback_error_handling(mock_persona_manager):
    """Test persona switch handles callback errors gracefully."""
    manager, jarvis, glados = mock_persona_manager
    manager.set_current_persona.return_value = True
    manager.get_current_persona.side_effect = [jarvis, glados]

    async def failing_callback(old, new):
        raise ValueError("Callback error")

    # Should not raise exception
    result = await switch_persona_handler("GLaDOS", manager, failing_callback)

    assert result["success"] == True  # Switch still succeeds


@pytest.mark.asyncio
async def test_tool_registry_integration(mock_persona_manager):
    """Test persona tool integrates with ToolRegistry."""
    manager, jarvis, glados = mock_persona_manager

    # Create registry and register tool
    registry = ToolRegistry()
    tool = create_persona_switch_tool(manager)
    registry.register_tool(tool)

    # Verify registration
    assert registry.get_tool("switch_persona") is not None
    assert "switch_persona" in [t["name"] for t in registry.get_tool_schemas()]

    # Test execution through registry
    manager.set_current_persona.return_value = True
    manager.get_current_persona.side_effect = [jarvis, glados]

    result = await registry.execute_tool("switch_persona", {"persona_name": "GLaDOS"})

    assert result["success"] == True
    assert result["result"]["persona"]["name"] == "GLaDOS"


def test_tool_schema_generation(mock_persona_manager):
    """Test tool schema for AI function calling."""
    manager, _, _ = mock_persona_manager

    tool = create_persona_switch_tool(manager)
    schema = tool.to_schema()

    assert schema["name"] == "switch_persona"
    assert "description" in schema
    assert schema["parameters"]["type"] == "object"
    assert "persona_name" in schema["parameters"]["properties"]
    assert schema["parameters"]["properties"]["persona_name"]["type"] == "string"
    assert schema["parameters"]["properties"]["persona_name"]["enum"] == ["JARVIS", "GLaDOS", "Samantha", "HAL9000"]
    assert "persona_name" in schema["parameters"]["required"]


def test_system_prompt_generation():
    """Test system prompt includes persona switching instructions."""
    prompt = get_persona_switching_system_prompt()

    assert "switch_persona" in prompt
    assert "TOOL_CALL" in prompt
    assert "persona_name" in prompt
    assert "When to Switch Personas" in prompt
    assert "How to Switch" in prompt


@pytest.mark.asyncio
async def test_multiple_sequential_switches(mock_persona_manager):
    """Test multiple persona switches in sequence."""
    manager, jarvis, glados = mock_persona_manager

    # First switch: JARVIS → GLaDOS
    manager.set_current_persona.return_value = True
    manager.get_current_persona.side_effect = [jarvis, glados]
    result1 = await switch_persona_handler("GLaDOS", manager)
    assert result1["success"] == True
    assert result1["persona"]["name"] == "GLaDOS"

    # Second switch: GLaDOS → JARVIS
    manager.get_current_persona.side_effect = [glados, jarvis]
    result2 = await switch_persona_handler("JARVIS", manager)
    assert result2["success"] == True
    assert result2["persona"]["name"] == "JARVIS"
    assert result2["previous_persona"] == "GLaDOS"


@pytest.mark.asyncio
async def test_switch_to_same_persona(mock_persona_manager):
    """Test switching to currently active persona."""
    manager, jarvis, _ = mock_persona_manager
    manager.set_current_persona.return_value = True
    manager.get_current_persona.side_effect = [jarvis, jarvis]

    result = await switch_persona_handler("JARVIS", manager)

    assert result["success"] == True
    assert result["persona"]["name"] == "JARVIS"
    assert result["previous_persona"] == "JARVIS"


@pytest.mark.asyncio
async def test_tool_descriptions(mock_persona_manager):
    """Test tool descriptions for LLM prompt."""
    manager, _, _ = mock_persona_manager

    registry = ToolRegistry()
    tool = create_persona_switch_tool(manager)
    registry.register_tool(tool)

    descriptions = registry.get_tool_descriptions()

    assert "switch_persona" in descriptions
    assert "persona_name" in descriptions
    assert "string" in descriptions
    assert "JARVIS" in descriptions or "GLaDOS" in descriptions  # Enum values


@pytest.mark.asyncio
async def test_no_initial_persona(mock_persona_manager):
    """Test switching when no persona is currently active."""
    manager, _, glados = mock_persona_manager
    manager.set_current_persona.return_value = True
    manager.get_current_persona.side_effect = [None, glados]

    result = await switch_persona_handler("GLaDOS", manager)

    assert result["success"] == True
    assert result["persona"]["name"] == "GLaDOS"
    assert result["previous_persona"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
