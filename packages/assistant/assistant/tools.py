"""
Core Tools Module - Registry, Parser, Executor, and Definitions.
Consolidated from previous tools/ package.
"""
import re
import os
import shlex
import psutil
import platform
import asyncio
import logging
import inspect
import toml
from typing import Dict, Callable, Any, Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import subprocess

# ==============================================================================
# REGISTRY & DATA STRUCTURES
# ==============================================================================

@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[str]] = None

@dataclass
class Tool:
    """Legacy Tool definition for ThinkingEngine compatibility."""
    name: str
    description: str
    parameters: List[ToolParameter]
    handler: Callable
    
    def to_schema(self) -> Dict[str, Any]:
        """Convert to JSON schema for function calling."""
        properties = {}
        required = []
        
        for param in self.parameters:
            param_schema = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                param_schema["enum"] = param.enum
            
            properties[param.name] = param_schema
            if param.required:
                required.append(param.name)
                
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }

@dataclass
class ToolDefinition:
    """Definition of a tool (New System)."""
    name: str
    description: str
    func: Callable
    parameters: Dict[str, Any]

class ToolRegistry:
    """
    Registry for all available tools.
    Allows registering functions as tools and retrieving them by name.
    """
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register_tool(self, tool: Any):
        """
        Register a tool object (Legacy/ThinkingEngine compatibility).
        Supports both new ToolDefinition and legacy Tool objects.
        """
        if hasattr(tool, 'func'): # ToolDefinition
            self._tools[tool.name] = tool
        elif hasattr(tool, 'handler'): # Legacy Tool
            # Convert legacy Tool to ToolDefinition-like wrapper
            tool_def = ToolDefinition(
                name=tool.name,
                description=tool.description,
                func=tool.handler,
                parameters={p.name: p.type for p in tool.parameters}
            )
            self._tools[tool.name] = tool_def
        elif callable(tool):
            # Direct function registration
            self.register(tool.__name__)(tool)

    def register(self, name: str, description: str = ""):
        """
        Decorator to register a function as a tool.
        """
        def decorator(func: Callable):
            sig = inspect.signature(func)
            params = {
                k: str(v.annotation) if v.annotation != inspect.Parameter.empty else "Any"
                for k, v in sig.parameters.items()
            }
            
            tool_def = ToolDefinition(
                name=name,
                description=description or func.__doc__ or "",
                func=func,
                parameters=params
            )
            self._tools[name] = tool_def
            return func
        return decorator

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, str]:
        return {name: tool.description for name, tool in self._tools.items()}

    async def execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name with arguments."""
        tool = self._tools.get(name)
        if not tool:
            return {"success": False, "message": f"Tool '{name}' not found"}
            
        try:
            if inspect.iscoroutinefunction(tool.func):
                result = await tool.func(**args)
            else:
                result = tool.func(**args)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_tool_descriptions(self) -> str:
        """Get a string description of all tools."""
        descriptions = []
        for name, tool in self._tools.items():
            param_str = ", ".join([f"{k}: {v}" for k, v in tool.parameters.items()])
            descriptions.append(f"- {name}({param_str}): {tool.description}")
        return "\n".join(descriptions)

    def get_tool_prompt(self) -> str:
        """Generate a prompt section listing available tools."""
        if not self._tools:
            return ""
            
        prompt = "## Available Tools\n"
        prompt += "You have access to the following tools. To use a tool, output a command in the format `[TOOL: tool_name arg1=value1 arg2=\"value with spaces\"]`.\n\n"
        
        for name, tool in self._tools.items():
            prompt += f"### {name}\n"
            prompt += f"{tool.description}\n"
            prompt += f"Usage: `[TOOL: {name} ...]`\n\n"
            
        return prompt

# Global registry instance
registry = ToolRegistry()


# ==============================================================================
# COMMAND PARSER
# ==============================================================================

class CommandParser:
    """Parses text for tool commands."""
    
    TOOL_REGEX = re.compile(r'\[TOOL:\s*([a-zA-Z0-9_]+)(?:\s+(.*?))?\]')

    @staticmethod
    def parse(text: str) -> List[Tuple[str, List[Any], Dict[str, Any]]]:
        commands = []
        for match in CommandParser.TOOL_REGEX.finditer(text):
            tool_name = match.group(1)
            args_str = match.group(2) or ""
            args = []
            kwargs = {}
            
            if args_str:
                try:
                    tokens = shlex.split(args_str)
                    for token in tokens:
                        if "=" in token:
                            key, value = token.split("=", 1)
                            kwargs[key] = value
                        else:
                            args.append(token)
                except ValueError:
                    pass
            
            commands.append((tool_name, args, kwargs))
        return commands

    @staticmethod
    def strip_commands(text: str) -> str:
        return CommandParser.TOOL_REGEX.sub('', text).strip()


# ==============================================================================
# TOOL EXECUTOR
# ==============================================================================

logger = logging.getLogger(__name__)

class ToolExecutor:
    """Executes tools found in text."""
    def __init__(self, registry_instance: ToolRegistry):
        self.registry = registry_instance

    async def execute(self, tool_name: str, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        tool_def = self.registry.get_tool(tool_name)
        if not tool_def:
            logger.warning(f"Tool '{tool_name}' not found")
            return f"Error: Tool '{tool_name}' not found"

        try:
            logger.info(f"Executing tool: {tool_name} args={args} kwargs={kwargs}")
            if asyncio.iscoroutinefunction(tool_def.func):
                result = await tool_def.func(*args, **kwargs)
            else:
                result = tool_def.func(*args, **kwargs)
            logger.info(f"Tool result: {result}")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"Error executing '{tool_name}': {str(e)}"

    async def execute_commands(self, commands: List[Tuple[str, List[Any], Dict[str, Any]]]) -> List[Any]:
        results = []
        for tool_name, args, kwargs in commands:
            result = await self.execute(tool_name, args, kwargs)
            results.append(result)
        return results


# ==============================================================================
# BASIC TOOLS (System, Filesystem, Terminal)
# ==============================================================================

@registry.register("get_system_stats", "Get current system statistics (CPU, RAM, Disk)")
def get_system_stats() -> str:
    """Get system statistics."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return (
        f"System Stats:\n"
        f"- OS: {platform.system()} {platform.release()}\n"
        f"- CPU Usage: {cpu_percent}%\n"
        f"- Memory: {memory.percent}% used ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)\n"
        f"- Disk: {disk.percent}% used ({disk.free // (1024**3)}GB free)"
    )

@registry.register("list_processes", "List top N processes by CPU usage")
def list_processes(limit: int = 5) -> str:
    """List top processes by CPU usage."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    processes.sort(key=lambda p: p['cpu_percent'] or 0, reverse=True)
    
    output = f"Top {limit} Processes by CPU:\n"
    for p in processes[:int(limit)]:
        output += f"- {p['name']} (PID: {p['pid']}): CPU {p['cpu_percent']}%, MEM {p['memory_percent']:.1f}%\n"
    return output

@registry.register("list_dir", "List contents of a directory")
def list_dir(path: str = ".") -> str:
    """List contents of a directory."""
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: Path '{path}' does not exist"
        if not p.is_dir():
            return f"Error: '{path}' is not a directory"
        items = []
        for item in p.iterdir():
            type_char = "d" if item.is_dir() else "f"
            items.append(f"[{type_char}] {item.name}")
        return f"Contents of {p}:\n" + "\n".join(sorted(items))
    except Exception as e:
        return f"Error listing directory: {e}"

@registry.register("read_file", "Read contents of a file (first N lines)")
def read_file(path: str, max_lines: int = 50) -> str:
    """Read file contents."""
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: File '{path}' does not exist"
        if not p.is_file():
            return f"Error: '{path}' is not a file"
        content = []
        with open(p, 'r', encoding='utf-8', errors='replace') as f:
            for i, line in enumerate(f):
                if i >= int(max_lines):
                    content.append(f"\n... (truncated after {max_lines} lines)")
                    break
                content.append(line.rstrip())
        return f"File: {p}\n" + "\n".join(content)
    except Exception as e:
        return f"Error reading file: {e}"

SAFE_COMMANDS = [
    "ls", "pwd", "echo", "cat", "grep", "find", "whoami", "date", "uptime",
    "git status", "git log", "git diff"
]

@registry.register("run_command", "Execute a shell command (restricted set)")
def run_command(command: str) -> str:
    """Execute a shell command."""
    cmd_parts = shlex.split(command)
    if not cmd_parts:
        return "Error: Empty command"
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        output = result.stdout
        if result.stderr:
            output += f"\nStderr: {result.stderr}"
        return output.strip() or "(No output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error executing command: {e}"


# ==============================================================================
# COMPLEX TOOLS (Theme, Email, Phone, Persona)
# ==============================================================================

class ThemeChangeTool:
    """Tool for changing assistant theme/persona."""
    @staticmethod
    def create_tool(app) -> Tool:
        async def change_theme_handler(persona_name: str) -> str:
            persona = app.persona_manager.get_persona(persona_name)
            if not persona:
                available = [p.name for p in app.available_personas]
                return f"Persona '{persona_name}' not found. Available personas: {', '.join(available)}"

            if not persona.theme or not persona.theme.theme_color:
                return f"Persona '{persona_name}' does not have a theme color defined."

            app.update_activity(f"🎨 Changing theme to {persona_name}...")
            app._theme_palette = app._load_theme(persona.theme.theme_color)
            app.theme_shade_1 = app._theme_palette.shade_1
            app.theme_shade_2 = app._theme_palette.shade_2
            app.theme_shade_3 = app._theme_palette.shade_3
            app.theme_shade_4 = app._theme_palette.shade_4
            app.theme_shade_5 = app._theme_palette.shade_5
            app.current_persona_name = persona.name
            
            try:
                visualizer = app.query_one("#visualizer")
                visualizer.border_title = f"xSwarm - {persona.name}"
            except Exception:
                pass

            app.config.default_persona = persona.name
            app.update_activity(f"✓ Theme changed to {persona.name}")
            asyncio.create_task(app.generate_greeting(re_introduction=True))
            return f"Successfully changed theme to {persona.name}. Theme color: {persona.theme.theme_color}. Re-introducing as {persona.name}..."

        available_personas = [p.name for p in app.available_personas if p.theme and p.theme.theme_color]
        return Tool(
            name="change_theme",
            description="Change the assistant's persona and theme colors.",
            parameters=[
                ToolParameter(
                    name="persona_name",
                    type="string",
                    description="Name of the persona to switch to",
                    required=True,
                    enum=available_personas
                )
            ],
            handler=change_theme_handler
        )

# Lazy imports for heavy dependencies
_mailer = None
_caller = None
_persona_manager = None

def get_persona_manager():
    global _persona_manager
    if _persona_manager is None:
        from .personas.manager import PersonaManager
        personas_dir = Path(__file__).parent.parent / "personas"
        # Fix path if needed based on new location
        if not personas_dir.exists():
             personas_dir = Path(__file__).parent / "personas"
        _persona_manager = PersonaManager(personas_dir=personas_dir)
    return _persona_manager

def get_mailer():
    global _mailer
    if _mailer is None:
        from .mailer import PersonaMailer
        _mailer = PersonaMailer()
    return _mailer

def get_caller():
    global _caller
    if _caller is None:
        from .phone import OutboundCaller
        _caller = OutboundCaller()
    return _caller

async def send_email_handler(subject: str, content: str, include_status_summary: bool = False, persona_name: str | None = None) -> Dict[str, Any]:
    try:
        to_email = os.getenv("USER_EMAIL") or os.getenv("XSWARM_DEV_ADMIN_EMAIL")
        if not to_email:
            return {"success": False, "message": "No recipient email configured."}

        persona_manager = get_persona_manager()
        if persona_name:
            persona = persona_manager.get_persona(persona_name)
        else:
            persona = persona_manager.get_current_persona()

        if not persona:
            return {"success": False, "message": f"Persona {persona_name or 'current'} not found"}

        if include_status_summary:
            content += "\n\n---\n**Development Status:**\nCurrently implementing full Moshi voice integration."

        mailer = get_mailer()
        result = await mailer.send_email(to_email=to_email, subject=subject, content=content, persona=persona)
        return result if result.get("success") else {"success": False, "message": f"Failed: {result.get('error')}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

send_email_tool = Tool(
    name="send_email",
    description="Send an email to the user.",
    parameters=[
        ToolParameter("subject", "string", "Email subject"),
        ToolParameter("content", "string", "Email body content"),
        ToolParameter("include_status_summary", "boolean", "Include dev status", required=False)
    ],
    handler=send_email_handler
)

async def make_call_handler(message: str, questions: Optional[list] = None, persona_name: str | None = None) -> Dict[str, Any]:
    try:
        to_number = os.getenv("USER_PHONE") or os.getenv("XSWARM_DEV_ADMIN_PHONE")
        if not to_number:
            config_path = Path("config.toml")
            if config_path.exists():
                config = toml.load(config_path)
                to_number = config.get("admin", {}).get("phone")
        if not to_number:
            return {"success": False, "message": "No phone number configured."}

        persona_manager = get_persona_manager()
        persona = persona_manager.get_persona(persona_name) if persona_name else persona_manager.get_current_persona()
        if not persona:
            return {"success": False, "message": "Persona not found"}

        caller = get_caller()
        result = await caller.make_call(to_number=to_number, message=message, persona=persona, questions=questions)
        return result if result.get("success") else {"success": False, "message": f"Failed: {result.get('error')}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

make_call_tool = Tool(
    name="make_call",
    description="Make a phone call to the user.",
    parameters=[
        ToolParameter("message", "string", "Message to speak"),
        ToolParameter("questions", "array", "Optional questions", required=False),
        ToolParameter("persona_name", "string", "Optional persona", required=False)
    ],
    handler=make_call_handler
)

def create_persona_switch_tool(persona_manager, on_persona_change=None) -> Tool:
    async def switch_persona_handler(persona_name: str, pm, cb=None) -> Dict[str, Any]:
        old_persona = pm.get_current_persona()
        success = pm.set_current_persona(persona_name)
        if not success:
            available = pm.list_personas()
            return {"success": False, "error": f"Persona '{persona_name}' not found", "available": available}
        
        new_persona = pm.get_current_persona()
        if cb:
            try:
                await cb(old_persona, new_persona)
            except Exception as e:
                logger.debug(f"Callback error: {e}")
        
        return {"success": True, "message": f"Switched to {new_persona.display_name}", "persona": {"name": new_persona.name}}

    available_personas = persona_manager.list_personas()
    return Tool(
        name="switch_persona",
        description="Switch the AI assistant's persona.",
        parameters=[
            ToolParameter("persona_name", "string", "Name of persona", enum=available_personas)
        ],
        handler=lambda persona_name: switch_persona_handler(persona_name, persona_manager, on_persona_change)
    )
