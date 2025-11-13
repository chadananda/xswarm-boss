"""
Persona Switch Tool - AI-powered persona switching via function calling.

Allows the AI assistant to dynamically switch personas during conversation
based on user requests or contextual triggers.

Usage:
    registry = ToolRegistry()
    persona_tool = create_persona_switch_tool(persona_manager)
    registry.register_tool(persona_tool)

    # AI can now call:
    # TOOL_CALL: {"name": "switch_persona", "arguments": {"persona_name": "JARVIS"}}
"""

from typing import Dict, Any, Optional, Callable
from assistant.tools.registry import Tool, ToolParameter
from assistant.personas.manager import PersonaManager


async def switch_persona_handler(
    persona_name: str,
    persona_manager: PersonaManager,
    on_persona_change: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Handler for persona switching tool.

    Args:
        persona_name: Name of persona to switch to (e.g., "JARVIS", "GLaDOS")
        persona_manager: PersonaManager instance
        on_persona_change: Optional callback for post-switch actions
                          Signature: async def callback(old_persona, new_persona)

    Returns:
        Dict with success status and persona info

    Examples:
        >>> result = await switch_persona_handler("JARVIS", manager)
        >>> result['success']
        True
        >>> result['persona']['name']
        'JARVIS'
    """
    # Get current persona for callback
    old_persona = persona_manager.get_current_persona()

    # Attempt switch
    success = persona_manager.set_current_persona(persona_name)

    if not success:
        # Persona not found - provide available options
        available = persona_manager.list_personas()
        return {
            "success": False,
            "error": f"Persona '{persona_name}' not found",
            "available_personas": available,
            "suggestion": f"Try one of: {', '.join(available)}"
        }

    # Get new persona
    new_persona = persona_manager.get_current_persona()

    # Invoke callback if provided (for TUI updates, voice reload, etc.)
    if on_persona_change:
        try:
            await on_persona_change(old_persona, new_persona)
        except Exception as e:
            print(f"⚠️  Persona change callback error: {e}")

    return {
        "success": True,
        "persona": {
            "name": new_persona.name,
            "display_name": new_persona.display_name,
            "theme_color": new_persona.theme_color,
            "description": new_persona.description
        },
        "message": f"Switched to {new_persona.display_name}",
        "previous_persona": old_persona.name if old_persona else None
    }


def create_persona_switch_tool(
    persona_manager: PersonaManager,
    on_persona_change: Optional[Callable] = None
) -> Tool:
    """
    Create PersonaSwitchTool for AI function calling.

    Args:
        persona_manager: PersonaManager instance
        on_persona_change: Optional async callback(old_persona, new_persona)

    Returns:
        Tool instance ready for registration

    Examples:
        >>> persona_tool = create_persona_switch_tool(manager)
        >>> registry.register_tool(persona_tool)
        >>> # AI can now switch personas via function calling
    """
    # Get available personas for enum
    available_personas = persona_manager.list_personas()

    # Create tool with persona enum
    tool = Tool(
        name="switch_persona",
        description=(
            "Switch the AI assistant's persona to change personality, voice, "
            "and interaction style. Use when user explicitly requests a persona "
            "change or when context suggests a different persona would be more appropriate."
        ),
        parameters=[
            ToolParameter(
                name="persona_name",
                type="string",
                description=(
                    "Name of the persona to switch to. Each persona has unique "
                    "personality traits, speaking style, and voice characteristics."
                ),
                required=True,
                enum=available_personas if available_personas else None
            )
        ],
        handler=lambda persona_name: switch_persona_handler(
            persona_name,
            persona_manager,
            on_persona_change
        )
    )

    return tool


def get_persona_switching_system_prompt() -> str:
    """
    Get system prompt instructions for persona switching.

    Include this in the AI's system prompt to enable intelligent persona switching.

    Returns:
        Formatted system prompt text

    Examples:
        >>> prompt = get_persona_switching_system_prompt()
        >>> system_message = base_prompt + "\n\n" + prompt
    """
    return """
# Persona Switching Capability

You have the ability to dynamically switch your persona during conversation using the `switch_persona` tool.

## When to Switch Personas

Switch personas when:
1. **User explicitly requests**: "Switch to JARVIS", "Be more like GLaDOS", "Act as Samantha"
2. **Contextual triggers**: Technical discussion → JARVIS, Gaming → GLaDOS, Emotional support → Samantha
3. **Mood changes**: User becomes frustrated → HAL 9000, playful → Wheatley

## How to Switch

Use the tool call format:
```
TOOL_CALL: {"name": "switch_persona", "arguments": {"persona_name": "JARVIS"}}
```

## After Switching

- Acknowledge the switch briefly: "Switching to JARVIS mode..."
- Immediately adopt the new persona's speaking style
- Continue the conversation naturally in the new persona

## Important Notes

- **Graceful transitions**: Don't abruptly change mid-sentence
- **User consent**: Confirm if switching without explicit request
- **Stay consistent**: Maintain the persona until switched again
- **Available personas**: Check tool parameters for valid options
"""


# =============================================================================
# INLINE TESTS
# =============================================================================

if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    from unittest.mock import Mock

    async def test_persona_switch_tool():
        """Test persona switch tool."""
        print("Testing Persona Switch Tool...\n")

        # Create mock persona manager
        manager = Mock(spec=PersonaManager)
        manager.list_personas.return_value = ["JARVIS", "GLaDOS", "Samantha"]
        manager.set_current_persona.return_value = True

        # Create mock personas
        old_persona = Mock()
        old_persona.name = "JARVIS"
        old_persona.display_name = "J.A.R.V.I.S."
        old_persona.theme_color = "#00D4FF"
        old_persona.description = "Just A Rather Very Intelligent System"

        new_persona = Mock()
        new_persona.name = "GLaDOS"
        new_persona.display_name = "GLaDOS"
        new_persona.theme_color = "#FFA500"
        new_persona.description = "Genetic Lifeform and Disk Operating System"

        manager.get_current_persona.return_value = old_persona

        # Test 1: Create tool
        print("1. Testing tool creation...")
        tool = create_persona_switch_tool(manager)
        assert tool.name == "switch_persona"
        assert len(tool.parameters) == 1
        assert tool.parameters[0].enum == ["JARVIS", "GLaDOS", "Samantha"]
        print("   ✓ Tool created with persona enum\n")

        # Test 2: Successful switch
        print("2. Testing successful persona switch...")
        manager.get_current_persona.side_effect = [old_persona, new_persona]
        result = await switch_persona_handler("GLaDOS", manager)
        assert result["success"] == True
        assert result["persona"]["name"] == "GLaDOS"
        assert result["previous_persona"] == "JARVIS"
        print(f"   ✓ Switched: {result['message']}\n")

        # Test 3: Failed switch (persona not found)
        print("3. Testing failed persona switch...")
        manager3 = Mock(spec=PersonaManager)
        manager3.list_personas.return_value = ["JARVIS", "GLaDOS", "Samantha"]
        manager3.set_current_persona.return_value = False
        manager3.get_current_persona.return_value = old_persona
        result = await switch_persona_handler("InvalidPersona", manager3)
        assert result["success"] == False
        assert "not found" in result["error"]
        assert "available_personas" in result
        print(f"   ✓ Failed gracefully: {result['error']}\n")

        # Test 4: With callback
        print("4. Testing with callback...")
        callback_called = False
        async def test_callback(old, new):
            nonlocal callback_called
            callback_called = True
            print(f"   → Callback: {old.name} → {new.name}")

        manager4 = Mock(spec=PersonaManager)
        manager4.set_current_persona.return_value = True
        manager4.get_current_persona.side_effect = [old_persona, new_persona]
        result = await switch_persona_handler("GLaDOS", manager4, test_callback)
        assert callback_called == True
        print("   ✓ Callback invoked\n")

        # Test 5: Tool schema
        print("5. Testing tool schema...")
        schema = tool.to_schema()
        assert schema["name"] == "switch_persona"
        assert "parameters" in schema
        assert schema["parameters"]["properties"]["persona_name"]["enum"] == ["JARVIS", "GLaDOS", "Samantha"]
        print(f"   ✓ Schema valid with enum: {schema['parameters']['properties']['persona_name']['enum']}\n")

        # Test 6: System prompt
        print("6. Testing system prompt...")
        prompt = get_persona_switching_system_prompt()
        assert "switch_persona" in prompt
        assert "TOOL_CALL" in prompt
        print("   ✓ System prompt generated\n")

        print("✅ All persona switch tool tests passed!")

    # Run tests
    asyncio.run(test_persona_switch_tool())
