"""
Comprehensive tests for tool calling system.

Tests:
- Tool registry creation and registration
- Tool parameter validation
- Tool execution success and failure
- Tool call parsing from LLM text
- Theme change tool functionality
- Tool descriptions generation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from assistant.tools import ToolRegistry, Tool, ToolParameter
from assistant.tools.theme_tool import ThemeChangeTool


class TestToolRegistry:
    """Test core tool registry functionality."""

    def test_registry_initialization(self):
        """Test registry starts empty."""
        registry = ToolRegistry()
        assert len(registry.tools) == 0
        assert registry.get_tool("nonexistent") is None

    def test_register_tool(self):
        """Test tool registration."""
        registry = ToolRegistry()

        async def dummy_handler(arg1: str):
            return f"handled: {arg1}"

        tool = Tool(
            name="test_tool",
            description="A test tool",
            parameters=[
                ToolParameter(name="arg1", type="string", description="First arg")
            ],
            handler=dummy_handler
        )

        registry.register_tool(tool)
        assert "test_tool" in registry.tools
        assert registry.get_tool("test_tool") == tool

    def test_get_tool_descriptions(self):
        """Test JSON schema generation."""
        registry = ToolRegistry()

        async def handler(persona_name: str):
            return "ok"

        tool = Tool(
            name="change_theme",
            description="Change assistant theme",
            parameters=[
                ToolParameter(
                    name="persona_name",
                    type="string",
                    description="Name of persona",
                    enum=["JARVIS", "GLaDOS"]
                )
            ],
            handler=handler
        )

        registry.register_tool(tool)
        descriptions = registry.get_tool_descriptions()

        assert "change_theme" in descriptions
        assert "persona_name" in descriptions
        assert "JARVIS" in descriptions
        assert "GLaDOS" in descriptions

    def test_parse_tool_call_valid(self):
        """Test parsing valid tool call."""
        registry = ToolRegistry()

        text = """Some text before
TOOL_CALL: {"name": "change_theme", "arguments": {"persona_name": "GLaDOS"}}
Some text after"""

        tool_call = registry.parse_tool_call(text)

        assert tool_call is not None
        assert tool_call["name"] == "change_theme"
        assert tool_call["arguments"]["persona_name"] == "GLaDOS"

    def test_parse_tool_call_no_tool(self):
        """Test parsing text without tool call."""
        registry = ToolRegistry()

        text = "Just normal text without any tool calls"
        tool_call = registry.parse_tool_call(text)

        assert tool_call is None

    def test_parse_tool_call_invalid_json(self):
        """Test parsing malformed JSON."""
        registry = ToolRegistry()

        text = "TOOL_CALL: {invalid json here}"

        # Implementation returns None for invalid JSON (graceful error handling)
        tool_call = registry.parse_tool_call(text)
        assert tool_call is None

    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Test successful tool execution."""
        registry = ToolRegistry()

        async def test_handler(arg1: str, arg2: int):
            return f"{arg1}:{arg2}"

        tool = Tool(
            name="test_tool",
            description="Test",
            parameters=[
                ToolParameter(name="arg1", type="string", description="Arg1"),
                ToolParameter(name="arg2", type="number", description="Arg2")
            ],
            handler=test_handler
        )

        registry.register_tool(tool)

        result = await registry.execute_tool(
            "test_tool",
            {"arg1": "hello", "arg2": 42}
        )

        assert result["success"] is True
        assert result["result"] == "hello:42"

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        """Test execution of non-existent tool."""
        registry = ToolRegistry()

        result = await registry.execute_tool("nonexistent", {})

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_tool_handler_error(self):
        """Test tool handler raises exception."""
        registry = ToolRegistry()

        async def failing_handler():
            raise ValueError("Something went wrong")

        tool = Tool(
            name="failing_tool",
            description="Fails",
            parameters=[],
            handler=failing_handler
        )

        registry.register_tool(tool)

        result = await registry.execute_tool("failing_tool", {})

        assert result["success"] is False
        assert "Something went wrong" in result["error"]


class TestThemeChangeTool:
    """Test theme change tool specifically."""

    @pytest.mark.asyncio
    async def test_theme_change_tool_success(self):
        """Test successful theme change."""
        # Create mock app
        mock_app = MagicMock()

        # Mock persona
        mock_persona = MagicMock()
        mock_persona.name = "GLaDOS"
        mock_persona.theme.theme_color = "#FFA500"

        # Mock persona manager
        mock_app.persona_manager.get_persona.return_value = mock_persona
        mock_app.available_personas = [mock_persona]

        # Mock theme palette
        mock_palette = MagicMock()
        mock_palette.shade_1 = "#FFA500"
        mock_palette.shade_2 = "#FFB933"
        mock_palette.shade_3 = "#FFCC66"
        mock_palette.shade_4 = "#FFE099"
        mock_palette.shade_5 = "#FFF5CC"
        mock_app._load_theme.return_value = mock_palette

        # Mock visualizer
        mock_visualizer = MagicMock()
        mock_app.query_one.return_value = mock_visualizer

        # Mock generate_greeting
        mock_app.generate_greeting = AsyncMock()

        # Create tool
        tool = ThemeChangeTool.create_tool(mock_app)

        # Execute
        result = await tool.handler(persona_name="GLaDOS")

        # Verify
        assert "Successfully changed theme to GLaDOS" in result
        mock_app.persona_manager.get_persona.assert_called_once_with("GLaDOS")
        mock_app._load_theme.assert_called_once_with("#FFA500")
        assert mock_app.theme_shade_1 == "#FFA500"
        mock_app.generate_greeting.assert_called_once_with(re_introduction=True)
        assert mock_visualizer.border_title == "xSwarm - GLaDOS"

    @pytest.mark.asyncio
    async def test_theme_change_tool_invalid_persona(self):
        """Test theme change with non-existent persona."""
        mock_app = MagicMock()

        # Persona not found
        mock_app.persona_manager.get_persona.return_value = None

        # Mock available personas
        mock_persona1 = MagicMock()
        mock_persona1.name = "JARVIS"
        mock_persona2 = MagicMock()
        mock_persona2.name = "GLaDOS"
        mock_app.available_personas = [mock_persona1, mock_persona2]

        tool = ThemeChangeTool.create_tool(mock_app)

        result = await tool.handler(persona_name="InvalidPersona")

        assert "not found" in result
        assert "JARVIS" in result
        assert "GLaDOS" in result

    def test_theme_tool_structure(self):
        """Test theme tool has correct structure."""
        mock_app = MagicMock()
        tool = ThemeChangeTool.create_tool(mock_app)

        assert tool.name == "change_theme"
        assert "theme" in tool.description.lower() or "persona" in tool.description.lower()
        assert len(tool.parameters) == 1

        param = tool.parameters[0]
        assert param.name == "persona_name"
        assert param.type == "string"
        assert param.required is True


class TestToolIntegration:
    """Integration tests for tool system."""

    @pytest.mark.asyncio
    async def test_full_tool_call_flow(self):
        """Test complete flow: parse → execute."""
        registry = ToolRegistry()

        # Register tool
        async def echo_handler(message: str):
            return f"Echo: {message}"

        tool = Tool(
            name="echo",
            description="Echo a message",
            parameters=[
                ToolParameter(name="message", type="string", description="Message to echo")
            ],
            handler=echo_handler
        )

        registry.register_tool(tool)

        # Simulate LLM output
        llm_output = 'I will echo your message. TOOL_CALL: {"name": "echo", "arguments": {"message": "Hello World"}}'

        # Parse
        tool_call = registry.parse_tool_call(llm_output)
        assert tool_call is not None

        # Execute
        result = await registry.execute_tool(
            tool_call["name"],
            tool_call["arguments"]
        )

        assert result["success"] is True
        assert result["result"] == "Echo: Hello World"

    def test_multiple_tools_registration(self):
        """Test registering multiple tools."""
        registry = ToolRegistry()

        async def handler1():
            pass

        async def handler2():
            pass

        tool1 = Tool("tool1", "First tool", [], handler1)
        tool2 = Tool("tool2", "Second tool", [], handler2)

        registry.register_tool(tool1)
        registry.register_tool(tool2)

        assert len(registry.tools) == 2
        assert registry.get_tool("tool1") == tool1
        assert registry.get_tool("tool2") == tool2

        descriptions = registry.get_tool_descriptions()
        assert "tool1" in descriptions
        assert "tool2" in descriptions
