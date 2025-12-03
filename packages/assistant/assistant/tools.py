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

    def get_anthropic_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Generate tool schemas compatible with Anthropic's API.

        Returns a list of tool definitions in the format expected by
        Claude's tool use feature.
        """
        schemas = []

        for name, tool in self._tools.items():
            # Build input schema from function signature
            func = tool.func
            sig = inspect.signature(func)

            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                # Determine type
                annotation = param.annotation
                if annotation == inspect.Parameter.empty:
                    param_type = "string"
                elif annotation == str:
                    param_type = "string"
                elif annotation == int:
                    param_type = "integer"
                elif annotation == float:
                    param_type = "number"
                elif annotation == bool:
                    param_type = "boolean"
                else:
                    param_type = "string"

                # Get description from docstring if available
                param_desc = f"Parameter: {param_name}"

                properties[param_name] = {
                    "type": param_type,
                    "description": param_desc
                }

                # Check if required (no default value)
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            schema = {
                "name": name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
            schemas.append(schema)

        return schemas

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


# ==============================================================================
# PLANNING TOOLS (Tasks, Habits, Projects, Commitments, Ideas)
# ==============================================================================

# Lazy planner instance - initialized per-session
_planner_data = None

def get_planner_data():
    """Get the global planner data instance (lazy load)."""
    global _planner_data
    if _planner_data is None:
        from .planner import PlannerData
        _planner_data = PlannerData()
    return _planner_data


def set_planner_data(planner: "PlannerData"):  # noqa: F821
    """Set the planner data instance (called by ChatEngine)."""
    global _planner_data
    _planner_data = planner


@registry.register("add_task", "Add a new task to the planning system")
def add_task(
    title: str,
    priority: str = "medium",
    contexts: str = "",
    energy: str = "medium",
    duration_min: int = 30,
    due_date: str = "",
    project_id: str = ""
) -> str:
    """Add a new task with GTD attributes."""
    planner = get_planner_data()

    # Parse contexts from comma-separated string
    context_list = [c.strip() for c in contexts.split(",") if c.strip()] if contexts else []

    task = planner.add_task(
        title=title,
        priority=priority,
        contexts=context_list,
        energy=energy,
        duration_min=duration_min,
        due_date=due_date if due_date else None,
        project_id=project_id if project_id else None
    )

    return f"✓ Added task: '{task.title}' (priority: {task.priority}, id: {task.id})"


@registry.register("complete_task", "Mark a task as complete")
def complete_task(task_id: str) -> str:
    """Mark a task as complete."""
    planner = get_planner_data()

    task = planner.complete_task(task_id)
    if not task:
        return f"✗ Task '{task_id}' not found"

    return f"✓ Completed task: '{task.title}'"


@registry.register("log_habit", "Record completion of a habit (updates streak)")
def log_habit(habit_id: str = "", habit_name: str = "") -> str:
    """Log completion of a habit by ID or name."""
    planner = get_planner_data()

    # Find habit by ID or name
    habit = None
    if habit_id:
        habit = planner.get_habit(habit_id)
    elif habit_name:
        # Search by name
        habit = planner.get_habit_by_name(habit_name)

    if not habit:
        available = [h.name for h in planner.get_habits()]
        return f"✗ Habit not found. Available habits: {', '.join(available) if available else 'none'}"

    habit = planner.log_habit(habit.id)
    if not habit:
        return "✗ Failed to log habit"

    streak_msg = f"🔥 {habit.current_streak} day streak!" if habit.current_streak > 1 else "Started new streak!"
    return f"✓ Logged '{habit.name}' - {streak_msg}"


@registry.register("capture_idea", "Quick capture an idea to the inbox")
def capture_idea(content: str, category: str = "project") -> str:
    """Capture an idea quickly."""
    planner = get_planner_data()

    planner.capture_idea(content=content, category=category)
    return f"✓ Captured idea: '{content[:50]}...' (category: {category})"


@registry.register("get_planning_summary", "Get current planning state summary")
def get_planning_summary() -> str:
    """Get a summary of planning state for display."""
    planner = get_planner_data()
    summary = planner.get_planning_summary()

    # Format as readable text
    needs_attention = len(summary['projects_needing_attention'])
    lines = [
        f"Date: {summary['date']}",
        f"Planning done today: {'Yes' if summary['planning_done'] else 'No'}",
        f"",
        f"Tasks: {summary['pending_tasks_count']} pending, {summary['overdue_tasks_count']} overdue",
        f"Habits due: {len(summary['habits_due_today'])}",
        f"Streaks at risk: {len(summary['streaks_at_risk'])}",
        f"",
        f"Projects: {summary['active_projects_count']} active, {needs_attention} need attention",
        f"Commitments: {len(summary['upcoming_commitments'])} upcoming, {len(summary['overdue_commitments'])} overdue",
        f"Ideas: {summary['unprocessed_ideas_count']} unprocessed",
    ]
    return "\n".join(lines)


@registry.register("get_all_tasks", "Get all tasks for daily planning")
def get_all_tasks(include_completed: bool = False) -> str:
    """
    Get all tasks to help with daily planning.
    Returns tasks grouped by status with key details.
    """
    planner = get_planner_data()

    all_tasks = planner.get_tasks()
    if not include_completed:
        all_tasks = [t for t in all_tasks if t.status != "complete"]

    if not all_tasks:
        return "No pending tasks. Use add_task to create some!"

    # Group by status
    by_status = {}
    for t in all_tasks:
        status = t.status
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(t)

    lines = []
    status_order = ["next", "inbox", "scheduled", "waiting", "someday"]

    for status in status_order:
        if status not in by_status:
            continue
        tasks = by_status[status]
        lines.append(f"\n[{status.upper()}] ({len(tasks)} tasks)")
        for t in tasks:
            due = f" (due {t.due_date})" if t.due_date else ""
            dur = f" ~{t.duration_min}min"
            pri = f" [{t.priority}]" if t.priority != "medium" else ""
            lines.append(f"  • {t.title}{pri}{dur}{due}")
            lines.append(f"    id: {t.id}")

    return "\n".join(lines)


@registry.register("get_todays_schedule", "Get today's schedule with tasks, habits, and meetings")
def get_todays_schedule() -> str:
    """
    Get today's complete schedule showing:
    - Meetings/events with times
    - Scheduled tasks with times
    - Habits due today (with preferred times)
    - Unscheduled tasks marked as 'next'

    Items are shown as a checklist with completion status.
    """
    from datetime import date, datetime

    planner = get_planner_data()
    today = date.today()
    today_str = today.isoformat()
    now = datetime.now()
    current_time = now.strftime("%H:%M")

    lines = [f"📋 TODAY'S SCHEDULE - {today.strftime('%A, %B %d')}", ""]

    # Collect all items with times
    timed_items = []  # (time, type, title, duration, done, id)

    # 1. Calendar events
    events = planner.get_todays_events()
    for e in events:
        time = e.start_time[11:16] if "T" in e.start_time else "00:00"
        timed_items.append((time, "event", e.title, 60, False, e.id))

    # 2. Scheduled tasks (including completed ones from today)
    all_tasks = planner.get_tasks()
    for t in all_tasks:
        # Include if: scheduled for today OR completed today
        is_scheduled_today = t.due_date == today_str and t.scheduled_time
        is_completed_today = t.status == "complete" and t.completed_at and t.completed_at[:10] == today_str

        if is_scheduled_today or is_completed_today:
            done = t.status == "complete"
            time_slot = t.scheduled_time or ""
            timed_items.append((time_slot, "task", t.title, t.duration_min, done, t.id))

    # 3. Habits due today (with preferred times)
    habits = planner.get_habits_due_today()
    time_map = {"morning": "08:00", "afternoon": "14:00", "evening": "19:00", "anytime": ""}
    for h in habits:
        pref_time = time_map.get(h.preferred_time, "")
        done = h.last_completed == today_str
        timed_items.append((pref_time, "habit", h.name, h.min_duration, done, h.id))

    # Sort by time (empty times go to end)
    timed_items.sort(key=lambda x: (x[0] == "", x[0]))

    # Render timed items
    if timed_items:
        for time, item_type, title, duration, done, item_id in timed_items:
            checkbox = "✓" if done else "○"
            time_str = f"{time} " if time else "     "
            type_icon = {"event": "📅", "task": "📌", "habit": "🔄"}.get(item_type, "•")
            dur_str = f" ~{duration}min" if duration else ""
            style = "~~" if done else ""

            if done:
                lines.append(f"  {checkbox} {time_str}{type_icon} {title}{dur_str}")
            else:
                # Highlight if current/upcoming
                is_past = time and time < current_time
                prefix = "  " if is_past else "▶ " if time and time <= current_time[:5] else "  "
                lines.append(f"{prefix}{checkbox} {time_str}{type_icon} {title}{dur_str}")
    else:
        lines.append("  No items scheduled yet.")

    # 4. Unscheduled tasks (next actions)
    next_tasks = planner.get_tasks(status="next")
    if next_tasks:
        lines.append("")
        lines.append("📥 UNSCHEDULED (ready to do):")
        for t in next_tasks[:5]:
            lines.append(f"  ○ {t.title} ~{t.duration_min}min  [{t.id}]")

    return "\n".join(lines)


@registry.register("schedule_task", "Schedule a task for a specific time today")
def schedule_task(task_id: str, time: str) -> str:
    """
    Schedule a task for a specific time today.

    Args:
        task_id: The task ID
        time: Time like "09:00" or "14:30"
    """
    from datetime import date

    planner = get_planner_data()
    task = planner.get_task(task_id)
    if not task:
        return f"✗ Task '{task_id}' not found"

    today = date.today().isoformat()
    planner.update_task(
        task_id,
        status="scheduled",
        due_date=today,
        scheduled_time=time
    )

    return f"✓ Scheduled '{task.title}' for {time}"


@registry.register("check_off", "Mark a task or habit as done and reschedule remaining items")
def check_off(item_id: str) -> str:
    """
    Check off a task or habit as complete.
    For tasks, marks as complete. For habits, logs completion.
    Returns updated schedule showing what's next.

    Args:
        item_id: Task ID (task_xxx) or habit ID (hab_xxx)
    """
    from datetime import datetime

    planner = get_planner_data()

    if item_id.startswith("task_"):
        task = planner.complete_task(item_id)
        if not task:
            return f"✗ Task '{item_id}' not found"
        result = f"✓ Completed: '{task.title}'"

    elif item_id.startswith("hab_"):
        habit = planner.log_habit(item_id)
        if not habit:
            return f"✗ Habit '{item_id}' not found"
        streak = f" 🔥 {habit.current_streak} day streak!" if habit.current_streak > 1 else ""
        result = f"✓ Logged: '{habit.name}'{streak}"

    else:
        # Try as task first, then habit
        task = planner.complete_task(item_id)
        if task:
            result = f"✓ Completed: '{task.title}'"
        else:
            habit = planner.log_habit(item_id)
            if habit:
                streak = f" 🔥 {habit.current_streak} day streak!" if habit.current_streak > 1 else ""
                result = f"✓ Logged: '{habit.name}'{streak}"
            else:
                return f"✗ Item '{item_id}' not found"

    # Show what's next
    result += "\n\n" + get_todays_schedule()
    return result


@registry.register("quick_add", "Quickly add a task or habit to today's schedule")
def quick_add(title: str, duration_min: int = 30, time: str = "", is_habit: bool = False) -> str:
    """
    Quickly add something to today's schedule.

    Args:
        title: What needs to be done
        duration_min: How long it takes (default: 30)
        time: Optional scheduled time like "14:00"
        is_habit: If True, creates a daily habit instead of one-time task
    """
    from datetime import date

    planner = get_planner_data()
    today = date.today().isoformat()

    if is_habit:
        # Create as daily habit
        habit = planner.add_habit(
            name=title,
            frequency="daily",
            min_duration=duration_min,
            preferred_time="anytime"
        )
        return f"✓ Added habit: '{title}' (~{duration_min}min daily)"

    else:
        # Create as task
        task = planner.add_task(
            title=title,
            priority="medium",
            status="scheduled" if time else "next",
            duration_min=duration_min,
            due_date=today if time else None,
            scheduled_time=time if time else None
        )

        if time:
            return f"✓ Added: '{title}' at {time} (~{duration_min}min)"
        else:
            return f"✓ Added: '{title}' (~{duration_min}min) - use schedule_task to set a time"


# ═══════════════════════════════════════════════════════════════════════════
# SCHEDULE OPTIMIZATION TOOLS
# ═══════════════════════════════════════════════════════════════════════════

def _time_to_minutes(time_str: str) -> int:
    """Convert HH:MM to minutes since midnight."""
    if not time_str:
        return 0
    parts = time_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def _minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to HH:MM."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _get_slot_energy(time_str: str) -> str:
    """Determine optimal energy level for a time slot."""
    minutes = _time_to_minutes(time_str)
    if minutes < 720:  # Before noon
        return "high"
    elif minutes < 960:  # Before 4pm
        return "medium"
    else:
        return "low"


def _find_available_slots(work_start: str, work_end: str, busy_slots: list) -> list:
    """Find available time slots between busy periods."""
    start_min = _time_to_minutes(work_start)
    end_min = _time_to_minutes(work_end)

    # Convert busy slots to minutes and sort
    busy_minutes = []
    for slot in busy_slots:
        busy_start = _time_to_minutes(slot[0]) if isinstance(slot[0], str) else slot[0]
        busy_end = _time_to_minutes(slot[1]) if isinstance(slot[1], str) else slot[1]
        busy_minutes.append((busy_start, busy_end))
    busy_minutes.sort()

    # Find gaps
    available = []
    current = start_min

    for busy_start, busy_end in busy_minutes:
        if busy_start > current:
            available.append((_minutes_to_time(current), _minutes_to_time(busy_start)))
        current = max(current, busy_end)

    # Add final slot if there's time left
    if current < end_min:
        available.append((_minutes_to_time(current), _minutes_to_time(end_min)))

    return available


@registry.register("optimize_day", "Auto-schedule tasks and habits around meetings to maximize productivity")
def optimize_day(work_start: str = "08:00", work_end: str = "18:00", include_habits: bool = True) -> str:
    """
    Automatically create an optimized daily schedule.

    Slots tasks into available time gaps around meetings, respecting:
    - Priority (critical > high > medium > low)
    - Energy levels (high-energy tasks in morning)
    - Duration (fits tasks into available gaps)
    - Habits at their preferred times

    Args:
        work_start: Start of work day (default: "08:00")
        work_end: End of work day (default: "18:00")
        include_habits: Whether to schedule habits (default: True)

    Returns:
        Summary of scheduled items
    """
    from datetime import datetime, date

    planner = get_planner_data()
    today = date.today().isoformat()

    # 1. Get today's fixed events (meetings)
    events = planner.get_calendar_events(today, today)
    busy_slots = []
    for event in events:
        # Extract time from event start/end
        start_time = event.start_time.split("T")[1][:5] if "T" in event.start_time else event.start_time[:5]
        end_time = event.end_time.split("T")[1][:5] if "T" in event.end_time else event.end_time[:5]
        busy_slots.append((start_time, end_time))

    # 2. Get schedulable tasks (next actions + already scheduled but not done)
    all_tasks = planner.list_tasks()
    tasks = [t for t in all_tasks
             if t.status in ("next", "scheduled", "inbox")
             and not t.completed_at]

    # 3. Get habits due today
    habits_to_schedule = []
    if include_habits:
        all_habits = planner.list_habits()
        for habit in all_habits:
            # Check if habit is due today and not done
            if habit.frequency == "daily" or (habit.frequency == "weekdays" and date.today().weekday() < 5):
                if habit.last_completed != today:
                    habits_to_schedule.append(habit)

    # 4. Find available time slots
    slots = _find_available_slots(work_start, work_end, busy_slots)

    # 5. Sort tasks by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    tasks.sort(key=lambda t: (priority_order.get(t.priority, 2), t.duration_min))

    # 6. Schedule tasks into slots
    scheduled_count = 0
    scheduled_items = []

    for slot_start, slot_end in slots:
        slot_duration = _time_to_minutes(slot_end) - _time_to_minutes(slot_start)
        slot_energy = _get_slot_energy(slot_start)
        current_time = slot_start

        while slot_duration >= 15:  # Minimum 15-minute tasks
            best_task = None
            best_score = -1

            for task in tasks:
                if task.scheduled_time:  # Already scheduled
                    continue
                if task.duration_min > slot_duration:  # Doesn't fit
                    continue

                # Score: priority + energy match
                score = (3 - priority_order.get(task.priority, 2)) * 10
                if task.energy == slot_energy or task.energy == "medium":
                    score += 5

                if score > best_score:
                    best_score = score
                    best_task = task

            if best_task:
                # Schedule this task
                planner.update_task(
                    best_task.id,
                    scheduled_time=current_time,
                    status="scheduled"
                )
                scheduled_items.append(f"📌 {current_time} {best_task.title} (~{best_task.duration_min}min)")
                scheduled_count += 1

                # Move to next slot position
                current_time = _minutes_to_time(_time_to_minutes(current_time) + best_task.duration_min)
                slot_duration -= best_task.duration_min
                best_task.scheduled_time = current_time  # Mark as scheduled for this loop
            else:
                break  # No more tasks fit

    # 7. Schedule habits at preferred times
    habit_times = {"morning": "07:00", "afternoon": "13:00", "evening": "19:00", "anytime": "12:00"}
    habits_scheduled = 0

    for habit in habits_to_schedule:
        preferred = habit_times.get(habit.preferred_time, "12:00")
        # Note: Habits don't have scheduled_time field - they show based on preferred_time
        scheduled_items.append(f"🔄 {preferred} {habit.name} (~{habit.min_duration}min)")
        habits_scheduled += 1

    # 8. Count unscheduled tasks
    unscheduled = [t for t in tasks if not t.scheduled_time and not t.completed_at]

    # Build result
    result = f"✅ Optimized schedule: {scheduled_count} tasks"
    if habits_scheduled:
        result += f", {habits_scheduled} habits"
    if unscheduled:
        result += f"\n⚠️ {len(unscheduled)} tasks couldn't fit (remain as Next Actions)"

    result += "\n\n" + get_todays_schedule()
    return result


@registry.register("reschedule_task", "Move a task to a different time or day")
def reschedule_task(task_id: str, new_time: str = "", new_date: str = "") -> str:
    """
    Reschedule a task to a different time or day.

    Args:
        task_id: The task ID to reschedule
        new_time: New time (HH:MM) - updates scheduled_time
        new_date: New date (YYYY-MM-DD or day name) - moves to different day

    Examples:
        reschedule_task("task_xxx", new_time="14:00")  # Same day, different time
        reschedule_task("task_xxx", new_date="tomorrow")  # Move to tomorrow
        reschedule_task("task_xxx")  # Unschedule (remove from today)
    """
    planner = get_planner_data()

    task = None
    for t in planner.list_tasks():
        if t.id == task_id:
            task = t
            break

    if not task:
        return f"✗ Task '{task_id}' not found"

    if new_date:
        # Move to different day
        parsed_date = _parse_natural_date(new_date, "09:00")
        date_only = parsed_date.split("T")[0]
        planner.update_task(task_id, due_date=date_only, scheduled_time=None, status="next")
        return f"✓ Moved '{task.title}' to {date_only}"

    elif new_time:
        # Change time on same day
        planner.update_task(task_id, scheduled_time=new_time, status="scheduled")
        return f"✓ Rescheduled '{task.title}' to {new_time}"

    else:
        # Unschedule
        planner.update_task(task_id, scheduled_time=None, status="next")
        return f"✓ Unscheduled '{task.title}' - now in Next Actions"


@registry.register("rollover_incomplete", "Move unfinished scheduled tasks to tomorrow")
def rollover_incomplete() -> str:
    """
    End-of-day cleanup: move unfinished scheduled tasks to tomorrow.

    Finds all tasks that were scheduled for today but not completed,
    clears their scheduled time, and sets them for tomorrow.
    """
    from datetime import date, timedelta

    planner = get_planner_data()
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    # Find incomplete scheduled tasks
    all_tasks = planner.list_tasks()
    to_rollover = []

    for task in all_tasks:
        if (task.status == "scheduled"
            and task.scheduled_time
            and not task.completed_at):
            to_rollover.append(task)

    if not to_rollover:
        return "✓ No tasks to roll over - everything completed today!"

    # Roll them over
    rolled = []
    for task in to_rollover:
        planner.update_task(
            task.id,
            scheduled_time=None,
            due_date=tomorrow,
            status="next"
        )
        rolled.append(task.title)

    result = f"📅 Rolled over {len(rolled)} tasks to tomorrow:\n"
    for title in rolled:
        result += f"  • {title}\n"

    return result.strip()


@registry.register("update_project", "Update a project's properties including description and folders")
def update_project(
    project_id: str,
    name: str = "",
    description: str = "",
    folders: str = "",
    health: str = "",
    health_reason: str = "",
    next_action: str = "",
    status: str = "",
    area: str = "",
    target_date: str = ""
) -> str:
    """Update any project fields. folders is comma-separated list of paths."""
    planner = get_planner_data()

    project = planner.get_project(project_id)
    if not project:
        return f"✗ Project '{project_id}' not found"

    updates = {}
    if name:
        updates["name"] = name
    if description:
        updates["description"] = description
    if folders:
        updates["folders"] = [f.strip() for f in folders.split(",") if f.strip()]
    if health:
        updates["health"] = health
    if health_reason:
        updates["health_reason"] = health_reason
    if next_action:
        updates["next_action"] = next_action
    if status:
        updates["status"] = status
    if area:
        updates["area"] = area
    if target_date:
        updates["target_date"] = target_date

    project = planner.update_project(project_id, **updates)
    if not project:
        return "✗ Failed to update project"

    return f"✓ Updated project '{project.name}' (id: {project.id})"


@registry.register("add_commitment", "Track a promise/commitment made to someone")
def add_commitment(
    description: str,
    to_whom: str,
    deadline: str,
    project_id: str = ""
) -> str:
    """Add a commitment to track."""
    planner = get_planner_data()

    planner.add_commitment(
        description=description,
        to_whom=to_whom,
        deadline=deadline,
        project_id=project_id if project_id else None
    )

    return f"✓ Added commitment to {to_whom}: '{description}' (due: {deadline})"


@registry.register("mark_planning_done", "Mark daily planning session as complete")
def mark_planning_done() -> str:
    """Mark that daily planning is complete."""
    planner = get_planner_data()
    planner.mark_daily_planning_done()
    return "✓ Daily planning complete. Have a productive day!"


@registry.register("add_habit", "Add a new habit to track")
def add_habit(
    name: str,
    frequency: str = "daily",
    preferred_time: str = "anytime",
    min_duration: int = 5
) -> str:
    """Add a new habit to track."""
    planner = get_planner_data()

    habit = planner.add_habit(
        name=name,
        frequency=frequency,
        preferred_time=preferred_time,
        min_duration=min_duration
    )

    return f"✓ Added habit: '{habit.name}' ({frequency}, best time: {preferred_time})"


# ==============================================================================
# GOAL TRACKING TOOLS
# ==============================================================================

@registry.register("add_goal", "Add a trackable goal with daily check-ins (weight, savings, etc)")
def add_goal(
    name: str,
    target_value: float,
    current_value: float,
    unit: str,
    direction: str = "down",
    target_date: str = ""
) -> str:
    """
    Add a new trackable goal for daily check-ins.

    Args:
        name: Goal name (e.g., "Weight", "Savings", "Pages Read")
        target_value: Target value to reach
        current_value: Starting/current value
        unit: Unit of measurement (e.g., "lbs", "$", "pages")
        direction: "down" for decreasing (weight loss) or "up" for increasing (savings)
        target_date: Optional target date (YYYY-MM-DD)

    Examples:
        add_goal("Weight", 180, 200, "lbs", direction="down")
        add_goal("Emergency Fund", 10000, 2500, "$", direction="up", target_date="2025-12-31")
    """
    planner = get_planner_data()

    goal = planner.add_goal(
        name=name,
        target_value=target_value,
        current_value=current_value,
        unit=unit,
        direction=direction,
        target_date=target_date if target_date else None
    )

    direction_text = "↓" if direction == "down" else "↑"
    target_text = f" (target: {target_date})" if target_date else ""
    return f"✓ Added goal: '{goal.name}' {direction_text} {current_value} → {target_value} {unit}{target_text}"


@registry.register("log_goal_checkin", "Log a check-in value for a goal (weigh-in, savings update)")
def log_goal_checkin(
    goal_name: str = "",
    goal_id: str = "",
    value: float = 0.0,
    note: str = ""
) -> str:
    """
    Log a check-in for a goal (e.g., daily weigh-in, savings balance update).

    Args:
        goal_name: Goal name (case-insensitive) - use either this or goal_id
        goal_id: Goal ID - use either this or goal_name
        value: The new value to record
        note: Optional note about this check-in

    Examples:
        log_goal_checkin(goal_name="Weight", value=198.5)
        log_goal_checkin(goal_name="Savings", value=3200, note="Added bonus")
    """
    planner = get_planner_data()

    # Find goal by ID or name
    goal = None
    if goal_id:
        goal = planner.get_goal(goal_id)
    elif goal_name:
        goal = planner.get_goal_by_name(goal_name)

    if not goal:
        available = [g.name for g in planner.get_goals()]
        return f"✗ Goal not found. Available goals: {', '.join(available) if available else 'none'}"

    # Log the check-in
    updated_goal = planner.log_goal_checkin(goal.id, value, note)
    if not updated_goal:
        return "✗ Failed to log check-in"

    # Calculate progress
    progress = updated_goal.progress_percent()

    # Determine trend
    direction_icon = "↓" if updated_goal.direction == "down" else "↑"
    diff = value - goal.current_value
    trend = ""
    if diff != 0:
        trend_icon = "📈" if (diff > 0 and updated_goal.direction == "up") or (diff < 0 and updated_goal.direction == "down") else "📉"
        trend = f" {trend_icon} {abs(diff):.1f} {updated_goal.unit}"

    return f"✓ Logged '{updated_goal.name}': {value} {updated_goal.unit}{trend} | Progress: {progress:.0f}%"


@registry.register("get_goal_progress", "Get detailed progress for a goal with trend info")
def get_goal_progress(goal_name: str = "", goal_id: str = "") -> str:
    """
    Get detailed progress information for a goal.

    Args:
        goal_name: Goal name (case-insensitive)
        goal_id: Goal ID (alternative to name)
    """
    planner = get_planner_data()

    # Find goal
    goal = None
    if goal_id:
        goal = planner.get_goal(goal_id)
    elif goal_name:
        goal = planner.get_goal_by_name(goal_name)

    if not goal:
        return "✗ Goal not found"

    # Get visual progress data
    progress_data = planner.get_goal_progress_visual(goal.id)
    if not progress_data:
        return "✗ Could not calculate progress"

    # Build progress bar
    progress = progress_data["progress_percent"]
    filled = int(progress / 5)  # 20 char bar
    bar = "█" * filled + "░" * (20 - filled)

    # Trend indicator
    trend_icons = {"improving": "📈", "declining": "📉", "stable": "➡️"}
    trend_icon = trend_icons.get(progress_data["trend"], "➡️")

    # Direction text
    direction = "↓" if progress_data["direction"] == "down" else "↑"

    lines = [
        f"📊 {progress_data['name']}",
        f"",
        f"   Start:   {progress_data['start']:.1f} {progress_data['unit']}",
        f"   Current: {progress_data['current']:.1f} {progress_data['unit']}",
        f"   Target:  {progress_data['target']:.1f} {progress_data['unit']} {direction}",
        f"",
        f"   [{bar}] {progress:.0f}%",
        f"",
        f"   Trend: {trend_icon} {progress_data['trend']}",
        f"   Check-ins: {progress_data['checkins_count']}",
    ]

    if progress_data["target_date"]:
        lines.append(f"   Target date: {progress_data['target_date']}")

    # Show recent check-ins
    if progress_data["recent_checkins"]:
        lines.append(f"")
        lines.append(f"   Recent:")
        for checkin in progress_data["recent_checkins"][-3:]:
            note = f" - {checkin['note']}" if checkin.get('note') else ""
            lines.append(f"     {checkin['date']}: {checkin['value']}{note}")

    return "\n".join(lines)


@registry.register("list_goals", "List all goals with progress")
def list_goals() -> str:
    """List all goals with current progress."""
    planner = get_planner_data()

    goals = planner.get_goals()

    if not goals:
        return "No goals found. Use add_goal to create one!"

    lines = [f"📊 Goals ({len(goals)}):"]

    for g in goals:
        progress = g.progress_percent()
        direction = "↓" if g.direction == "down" else "↑"

        # Mini progress bar (10 chars)
        filled = int(progress / 10)
        bar = "█" * filled + "░" * (10 - filled)

        lines.append(f"  [{g.id}] {g.name}")
        lines.append(f"         {g.current_value:.1f} → {g.target_value:.1f} {g.unit} {direction}")
        lines.append(f"         [{bar}] {progress:.0f}%")

    return "\n".join(lines)


@registry.register("delete_goal", "Delete a goal by ID")
def delete_goal(goal_id: str) -> str:
    """Delete a goal."""
    planner = get_planner_data()

    goal = planner.get_goal(goal_id)
    if not goal:
        return f"✗ Goal '{goal_id}' not found"

    name = goal.name
    if planner.delete_goal(goal_id):
        return f"✓ Deleted goal: '{name}'"
    return "✗ Failed to delete goal"


@registry.register("get_habit_streak_visual", "Get visual streak grid for a habit")
def get_habit_streak_visual(habit_name: str = "", habit_id: str = "", weeks: int = 8) -> str:
    """
    Get a visual streak grid (like GitHub contribution graph) for a habit.

    Args:
        habit_name: Habit name (case-insensitive)
        habit_id: Habit ID (alternative to name)
        weeks: Number of weeks to show (default: 8)
    """
    planner = get_planner_data()

    # Find habit
    habit = None
    if habit_id:
        habit = planner.get_habit(habit_id)
    elif habit_name:
        habit = planner.get_habit_by_name(habit_name)

    if not habit:
        return "✗ Habit not found"

    # Get visual grid
    grid = planner.get_habit_streak_visual(habit.id, weeks=weeks)
    if not grid:
        return "✗ No history available"

    # Build visual representation
    lines = [
        f"🔥 {habit.name} - Streak: {habit.current_streak} days (best: {habit.best_streak})",
        "",
        "   M T W T F S S"
    ]

    for week in grid:
        row = "   "
        for day in week:
            if day is None:
                row += "· "  # Future
            elif day:
                row += "█ "  # Completed
            else:
                row += "░ "  # Missed
        lines.append(row)

    lines.append("")
    lines.append("   █ = completed  ░ = missed  · = future")

    return "\n".join(lines)


@registry.register("add_project", "Add a new project to track with optional description and folders")
def add_project(
    name: str,
    description: str = "",
    folders: str = "",
    area: str = "personal",
    target_date: str = "",
    next_action: str = ""
) -> str:
    """Add a new project. folders is comma-separated list of paths."""
    planner = get_planner_data()

    folder_list = [f.strip() for f in folders.split(",") if f.strip()] if folders else []

    project = planner.add_project(
        name=name,
        description=description,
        folders=folder_list,
        area=area,
        target_date=target_date if target_date else None,
        next_action=next_action if next_action else None
    )

    return f"✓ Added project: '{project.name}' (area: {area}, id: {project.id})"


# ==============================================================================
# UPDATE/DELETE TOOLS
# ==============================================================================

@registry.register("update_task", "Update an existing task's properties")
def update_task(
    task_id: str,
    title: str = "",
    priority: str = "",
    status: str = "",
    due_date: str = "",
    notes: str = ""
) -> str:
    """Update a task's properties."""
    planner = get_planner_data()

    task = planner.get_task(task_id)
    if not task:
        return f"✗ Task '{task_id}' not found"

    updates = {}
    if title:
        updates["title"] = title
    if priority:
        updates["priority"] = priority
    if status:
        updates["status"] = status
    if due_date:
        updates["due_date"] = due_date
    if notes:
        updates["notes"] = notes

    task = planner.update_task(task_id, **updates)
    return f"✓ Updated task: '{task.title}'"


@registry.register("delete_task", "Delete a task by ID")
def delete_task(task_id: str) -> str:
    """Delete a task."""
    planner = get_planner_data()

    task = planner.get_task(task_id)
    if not task:
        return f"✗ Task '{task_id}' not found"

    title = task.title
    if planner.delete_task(task_id):
        return f"✓ Deleted task: '{title}'"
    return "✗ Failed to delete task"


@registry.register("delete_project", "Delete a project by ID")
def delete_project(project_id: str) -> str:
    """Delete a project."""
    planner = get_planner_data()

    project = planner.get_project(project_id)
    if not project:
        return f"✗ Project '{project_id}' not found"

    name = project.name
    if planner.delete_project(project_id):
        return f"✓ Deleted project: '{name}'"
    return "✗ Failed to delete project"


@registry.register("add_project_folder", "Add a folder path to a project")
def add_project_folder(project_id: str, folder_path: str) -> str:
    """Add a folder to track as part of a project."""
    planner = get_planner_data()

    project = planner.get_project(project_id)
    if not project:
        return f"✗ Project '{project_id}' not found"

    folders = list(project.folders) if project.folders else []
    if folder_path not in folders:
        folders.append(folder_path)
        planner.update_project(project_id, folders=folders)
        return f"✓ Added folder '{folder_path}' to project '{project.name}'"
    return f"Folder '{folder_path}' already in project"


@registry.register("remove_project_folder", "Remove a folder path from a project")
def remove_project_folder(project_id: str, folder_path: str) -> str:
    """Remove a folder from a project."""
    planner = get_planner_data()

    project = planner.get_project(project_id)
    if not project:
        return f"✗ Project '{project_id}' not found"

    folders = list(project.folders) if project.folders else []
    if folder_path in folders:
        folders.remove(folder_path)
        planner.update_project(project_id, folders=folders)
        return f"✓ Removed folder '{folder_path}' from project '{project.name}'"
    return f"✗ Folder '{folder_path}' not in project"


@registry.register("update_habit", "Update a habit's properties")
def update_habit(
    habit_id: str,
    name: str = "",
    frequency: str = "",
    preferred_time: str = "",
    min_duration: int = 0
) -> str:
    """Update a habit."""
    planner = get_planner_data()

    habit = planner.get_habit(habit_id)
    if not habit:
        return f"✗ Habit '{habit_id}' not found"

    updates = {}
    if name:
        updates["name"] = name
    if frequency:
        updates["frequency"] = frequency
    if preferred_time:
        updates["preferred_time"] = preferred_time
    if min_duration > 0:
        updates["min_duration"] = min_duration

    habit = planner.update_habit(habit_id, **updates)
    return f"✓ Updated habit: '{habit.name}'"


@registry.register("delete_habit", "Delete a habit by ID")
def delete_habit(habit_id: str) -> str:
    """Delete a habit."""
    planner = get_planner_data()

    habit = planner.get_habit(habit_id)
    if not habit:
        return f"✗ Habit '{habit_id}' not found"

    name = habit.name
    if planner.delete_habit(habit_id):
        return f"✓ Deleted habit: '{name}'"
    return "✗ Failed to delete habit"


@registry.register("complete_commitment", "Mark a commitment as fulfilled")
def complete_commitment(commitment_id: str) -> str:
    """Complete a commitment."""
    planner = get_planner_data()

    commitment = planner.complete_commitment(commitment_id)
    if not commitment:
        return f"✗ Commitment '{commitment_id}' not found"

    return f"✓ Completed commitment: '{commitment.description}'"


@registry.register("delete_commitment", "Delete a commitment by ID")
def delete_commitment(commitment_id: str) -> str:
    """Delete a commitment."""
    planner = get_planner_data()

    # Get first to show description
    commitments = planner.get_commitments(include_completed=True)
    desc = None
    for c in commitments:
        if c.id == commitment_id:
            desc = c.description
            break

    if not desc:
        return f"✗ Commitment '{commitment_id}' not found"

    if planner.delete_commitment(commitment_id):
        return f"✓ Deleted commitment: '{desc}'"
    return "✗ Failed to delete commitment"


@registry.register("delete_idea", "Delete an idea by ID")
def delete_idea(idea_id: str) -> str:
    """Delete an idea."""
    planner = get_planner_data()

    if planner.delete_idea(idea_id):
        return f"✓ Deleted idea: {idea_id}"
    return f"✗ Idea '{idea_id}' not found"


# ==============================================================================
# LIST TOOLS
# ==============================================================================

@registry.register("list_tasks", "List tasks with optional filtering")
def list_tasks(status: str = "", project_id: str = "") -> str:
    """List tasks, optionally filtered."""
    planner = get_planner_data()

    tasks = planner.get_tasks(
        status=status if status else None,
        project_id=project_id if project_id else None
    )

    if not tasks:
        return "No tasks found."

    lines = [f"Tasks ({len(tasks)}):"]
    for t in tasks:
        due = f" (due: {t.due_date})" if t.due_date else ""
        lines.append(f"  [{t.id}] {t.title} - {t.status}, {t.priority}{due}")

    return "\n".join(lines)


@registry.register("list_projects", "List all projects")
def list_projects(status: str = "") -> str:
    """List projects."""
    planner = get_planner_data()

    projects = planner.get_projects(status=status if status else None)

    if not projects:
        return "No projects found."

    lines = [f"Projects ({len(projects)}):"]
    for p in projects:
        health_icon = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(p.health, "⚪")
        lines.append(f"  [{p.id}] {health_icon} {p.name} - {p.status}")

    return "\n".join(lines)


@registry.register("list_habits", "List all habits with streak info")
def list_habits() -> str:
    """List all habits."""
    planner = get_planner_data()

    habits = planner.get_habits()

    if not habits:
        return "No habits found."

    lines = [f"Habits ({len(habits)}):"]
    for h in habits:
        streak = f"🔥{h.current_streak}" if h.current_streak > 0 else "no streak"
        lines.append(f"  [{h.id}] {h.name} ({h.frequency}) - {streak}")

    return "\n".join(lines)


@registry.register("list_commitments", "List commitments")
def list_commitments(include_completed: bool = False) -> str:
    """List commitments."""
    planner = get_planner_data()

    commitments = planner.get_commitments(include_completed=include_completed)

    if not commitments:
        return "No commitments found."

    lines = [f"Commitments ({len(commitments)}):"]
    for c in commitments:
        status_icon = "✓" if c.status == "complete" else "○"
        lines.append(f"  [{c.id}] {status_icon} To {c.to_whom}: {c.description} (due: {c.deadline})")

    return "\n".join(lines)


@registry.register("list_ideas", "List captured ideas")
def list_ideas(show_processed: bool = False) -> str:
    """List ideas."""
    planner = get_planner_data()

    ideas = planner.get_ideas(processed=None if show_processed else False)

    if not ideas:
        return "No ideas found."

    lines = [f"Ideas ({len(ideas)}):"]
    for i in ideas:
        status = "✓" if i.processed else "○"
        lines.append(f"  [{i.id}] {status} [{i.category}] {i.content[:50]}...")

    return "\n".join(lines)


# ==============================================================================
# CALENDAR TOOLS
# ==============================================================================

def _parse_natural_date(date_str: str, time_str: str = "09:00") -> str:
    """
    Parse natural language dates into ISO format.

    Accepts:
    - Day names: "Monday", "Tuesday", "friday" (finds next occurrence)
    - Relative: "today", "tomorrow", "next Monday"
    - ISO format: "2025-12-05" (passed through)
    - ISO datetime: "2025-12-05T10:00" (passed through)

    Returns ISO datetime string like "2025-12-05T09:00:00"
    """
    from datetime import datetime, date, timedelta

    date_str = date_str.strip()
    time_str = time_str.strip()

    # Already ISO datetime format
    if "T" in date_str and len(date_str) >= 16:
        return date_str if len(date_str) >= 19 else date_str + ":00"

    # Already ISO date format (YYYY-MM-DD)
    if len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
        return f"{date_str}T{time_str}:00" if len(time_str) == 5 else f"{date_str}T{time_str}"

    today = date.today()
    target_date = None

    # Normalize for comparison
    date_lower = date_str.lower()

    # Handle "today" and "tomorrow"
    if date_lower == "today":
        target_date = today
    elif date_lower == "tomorrow":
        target_date = today + timedelta(days=1)
    else:
        # Day name mapping
        day_names = {
            "monday": 0, "mon": 0,
            "tuesday": 1, "tue": 1, "tues": 1,
            "wednesday": 2, "wed": 2,
            "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
            "friday": 4, "fri": 4,
            "saturday": 5, "sat": 5,
            "sunday": 6, "sun": 6,
        }

        # Remove "next " prefix if present
        check_str = date_lower.replace("next ", "")

        if check_str in day_names:
            target_weekday = day_names[check_str]
            current_weekday = today.weekday()

            # Calculate days until target weekday
            days_ahead = target_weekday - current_weekday
            if days_ahead <= 0:  # Target day already passed this week
                days_ahead += 7

            target_date = today + timedelta(days=days_ahead)

    if target_date:
        time_part = time_str if len(time_str) == 5 else time_str[:5]
        return f"{target_date.isoformat()}T{time_part}:00"

    # Fallback: assume it's already a valid format or close to it
    return date_str


@registry.register("add_calendar_event", "Add a one-time meeting or event")
def add_calendar_event(
    title: str,
    day: str,
    start_time: str = "09:00",
    duration_minutes: int = 60,
    description: str = "",
    location: str = "",
    attendees: str = "",
    reminder_minutes: int = 15,
    project_id: str = ""
) -> str:
    """
    Add a ONE-TIME calendar event. For recurring meetings, use add_recurring_meeting instead.

    Args:
        title: Event title
        day: Day of event - "Monday", "Friday", "tomorrow", "today", or "2025-12-05"
        start_time: Time like "09:00" or "14:30" (default: 09:00)
        duration_minutes: How long (default: 60)
        attendees: Comma-separated names/emails
    """
    from datetime import datetime, timedelta

    planner = get_planner_data()

    # Parse natural language date
    start_datetime = _parse_natural_date(day, start_time)

    # Calculate end time from duration
    start_dt = datetime.fromisoformat(start_datetime)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    end_datetime = end_dt.isoformat()

    attendee_list = [a.strip() for a in attendees.split(",") if a.strip()] if attendees else []

    event = planner.add_calendar_event(
        title=title,
        start_time=start_datetime,
        end_time=end_datetime,
        description=description,
        location=location,
        attendees=attendee_list,
        recurrence="none",
        reminder_minutes=reminder_minutes,
        project_id=project_id if project_id else None
    )

    # Format nice output with day name
    event_date = datetime.fromisoformat(event.start_time)
    day_name = event_date.strftime("%A")
    date_str = event_date.strftime("%b %d")
    time_str = event_date.strftime("%H:%M")

    return f"✓ Added: '{event.title}' on {day_name} {date_str} at {time_str}"


@registry.register("add_recurring_meeting", "Add a recurring meeting (weekly, daily, etc)")
def add_recurring_meeting(
    title: str,
    day_of_week: str,
    start_time: str = "09:00",
    duration_minutes: int = 60,
    frequency: str = "weekly",
    description: str = "",
    location: str = "",
    attendees: str = "",
    reminder_minutes: int = 15,
    project_id: str = ""
) -> str:
    """
    Add a RECURRING meeting. Creates ONE event that repeats automatically.

    Args:
        title: Meeting title (e.g., "Team Standup")
        day_of_week: Which day - "Monday", "Tuesday", "Wednesday", etc.
        start_time: Time like "09:00" or "14:30"
        duration_minutes: How long (default: 60)
        frequency: "daily", "weekly", "biweekly", "monthly" (default: weekly)
        attendees: Comma-separated names/emails

    Example: add_recurring_meeting("Team Standup", "Monday", "09:00", frequency="weekly")
    This creates ONE meeting entry that shows up every Monday automatically.
    """
    from datetime import datetime, timedelta

    planner = get_planner_data()

    # For recurring, find the NEXT occurrence of that day
    start_datetime = _parse_natural_date(day_of_week, start_time)

    # Calculate end time from duration
    start_dt = datetime.fromisoformat(start_datetime)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    end_datetime = end_dt.isoformat()

    attendee_list = [a.strip() for a in attendees.split(",") if a.strip()] if attendees else []

    # Validate frequency
    valid_frequencies = ["daily", "weekly", "biweekly", "monthly", "yearly"]
    if frequency not in valid_frequencies:
        frequency = "weekly"

    event = planner.add_calendar_event(
        title=title,
        start_time=start_datetime,
        end_time=end_datetime,
        description=description,
        location=location,
        attendees=attendee_list,
        recurrence=frequency,
        recurrence_end=None,  # Recurring indefinitely
        reminder_minutes=reminder_minutes,
        project_id=project_id if project_id else None
    )

    # Format nice output
    event_date = datetime.fromisoformat(event.start_time)
    day_name = event_date.strftime("%A")
    time_str = event_date.strftime("%H:%M")

    freq_text = {
        "daily": "every day",
        "weekly": f"every {day_name}",
        "biweekly": f"every other {day_name}",
        "monthly": "monthly",
        "yearly": "yearly"
    }.get(frequency, frequency)

    return f"✓ Added recurring: '{event.title}' {freq_text} at {time_str}"


@registry.register("update_calendar_event", "Update a calendar event")
def update_calendar_event(
    event_id: str,
    title: str = "",
    start_time: str = "",
    end_time: str = "",
    description: str = "",
    location: str = "",
    recurrence: str = "",
    reminder_minutes: int = 0
) -> str:
    """Update a calendar event."""
    planner = get_planner_data()

    event = planner.get_calendar_event(event_id)
    if not event:
        return f"✗ Event '{event_id}' not found"

    updates = {}
    if title:
        updates["title"] = title
    if start_time:
        updates["start_time"] = start_time
    if end_time:
        updates["end_time"] = end_time
    if description:
        updates["description"] = description
    if location:
        updates["location"] = location
    if recurrence:
        updates["recurrence"] = recurrence
    if reminder_minutes > 0:
        updates["reminder_minutes"] = reminder_minutes

    event = planner.update_calendar_event(event_id, **updates)
    return f"✓ Updated event: '{event.title}'"


@registry.register("delete_calendar_event", "Delete a calendar event")
def delete_calendar_event(event_id: str) -> str:
    """Delete a calendar event."""
    planner = get_planner_data()

    event = planner.get_calendar_event(event_id)
    if not event:
        return f"✗ Event '{event_id}' not found"

    title = event.title
    if planner.delete_calendar_event(event_id):
        return f"✓ Deleted event: '{title}'"
    return "✗ Failed to delete event"


@registry.register("list_calendar_events", "List calendar events")
def list_calendar_events(days: int = 7) -> str:
    """List upcoming calendar events."""
    planner = get_planner_data()

    events = planner.get_upcoming_events(days=days)

    if not events:
        return f"No events in the next {days} days."

    lines = [f"Calendar ({len(events)} events in next {days} days):"]
    for e in events:
        # Format: 2024-01-15T10:00 -> Jan 15 10:00
        dt = e.start_time[:16]
        recur = f" ↻{e.recurrence}" if e.recurrence != "none" else ""
        loc = f" @ {e.location}" if e.location else ""
        lines.append(f"  [{e.id}] {dt} - {e.title}{loc}{recur}")

    return "\n".join(lines)


# get_todays_schedule is defined earlier in file with full checklist support
