"""
Tool registry system for function calling.

Manages available tools and provides schema for Moshi LLM.
"""

from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass
import json


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str  # "string", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    enum: Optional[List[str]] = None  # For choice parameters


@dataclass
class Tool:
    """Tool definition with schema and execution handler."""
    name: str
    description: str
    parameters: List[ToolParameter]
    handler: Callable  # Async function that executes the tool

    def to_schema(self) -> Dict[str, Any]:
        """Convert tool to JSON schema format for LLM."""
        params_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for param in self.parameters:
            param_def = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                param_def["enum"] = param.enum

            params_schema["properties"][param.name] = param_def
            if param.required:
                params_schema["required"].append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": params_schema
        }


class ToolRegistry:
    """
    Registry for available tools.

    Provides tool schemas to LLM and executes tool calls.
    """

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool):
        """Register a new tool."""
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self.tools.get(name)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get all tool schemas for LLM context."""
        return [tool.to_schema() for tool in self.tools.values()]

    def get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions for LLM prompt."""
        if not self.tools:
            return "No tools available."

        descriptions = ["Available tools:"]
        for tool in self.tools.values():
            descriptions.append(f"\n{tool.name}: {tool.description}")
            if tool.parameters:
                descriptions.append("  Parameters:")
                for param in tool.parameters:
                    required = " (required)" if param.required else " (optional)"
                    enum_info = f" [choices: {', '.join(param.enum)}]" if param.enum else ""
                    descriptions.append(f"    - {param.name} ({param.type}){required}: {param.description}{enum_info}")

        return "\n".join(descriptions)

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call.

        Returns:
            Dict with 'success' bool and 'result' or 'error' message
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }

        try:
            result = await tool.handler(**arguments)
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse tool call from LLM response.

        Expected format: TOOL_CALL: {"name": "tool_name", "arguments": {...}}

        Returns:
            Dict with 'name' and 'arguments', or None if no tool call found
        """
        if "TOOL_CALL:" not in text:
            return None

        try:
            # Extract JSON after TOOL_CALL:
            tool_start = text.find("TOOL_CALL:")
            json_start = text.find("{", tool_start)
            json_end = text.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                return None

            tool_json = text[json_start:json_end]
            tool_call = json.loads(tool_json)

            return tool_call
        except json.JSONDecodeError:
            return None
