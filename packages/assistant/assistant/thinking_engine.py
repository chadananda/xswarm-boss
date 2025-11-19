"""
Thinking Engine - Monitors conversations and decides on tool/memory usage.

The thinking engine runs in the background, watching both user input and
Moshi's output. It uses Claude to decide when to:
- Search memory for relevant context
- Execute tools (email, phone, etc.)
- Inject memories/reminders into Moshi's context

This is the "brain" that gives Moshi access to external capabilities.
"""

import asyncio
import os
from typing import Optional, Dict, Any, List
from anthropic import AsyncAnthropic

from .tools.registry import ToolRegistry, Tool, ToolParameter
from .tools.email_tool import send_email_tool
from .tools.phone_tool import make_call_tool
from .memory import MemoryManager


class ThinkingEngine:
    """
    Background thinking system that monitors conversations and acts.

    Watches:
    - User speech/text input
    - Moshi's spoken output

    Decides:
    - Should we search memory for relevant info?
    - Should we execute a tool?
    - Should we inject context to help Moshi?
    """

    def __init__(
        self,
        voice_client,  # VoiceServerClient
        memory_manager: Optional[MemoryManager] = None,
        user_id: str = "default-user"
    ):
        self.voice_client = voice_client
        self.memory_manager = memory_manager
        self.user_id = user_id

        # Claude client for thinking
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.claude = AsyncAnthropic(api_key=api_key) if api_key else None

        # Tool registry
        self.tool_registry = ToolRegistry()
        self._register_tools()

        # State
        self.running = False
        self.poll_interval = 0.5  # seconds
        self.last_user_input = ""
        self.last_moshi_output = ""
        self.conversation_buffer = []  # Recent conversation for context
        self.max_buffer_size = 20

        # Callbacks
        self.on_injection: Optional[callable] = None  # Called when context injected
        self.on_tool_result: Optional[callable] = None  # Called when tool executed

    def _register_tools(self):
        """Register available tools."""
        self.tool_registry.register_tool(send_email_tool)
        try:
            self.tool_registry.register_tool(make_call_tool)
        except Exception:
            pass  # Phone tool may not be available

        # Memory search tool
        memory_search_tool = Tool(
            name="search_memory",
            description="Search conversation memory for relevant past interactions, user preferences, or important information.",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="What to search for in memory",
                    required=True
                )
            ],
            handler=self._search_memory_handler
        )
        self.tool_registry.register_tool(memory_search_tool)

    async def _search_memory_handler(self, query: str) -> Dict[str, Any]:
        """Handle memory search requests."""
        if not self.memory_manager:
            return {"success": False, "message": "Memory not available"}

        # Get recent context that might be relevant
        context = await self.memory_manager.get_context(self.user_id, limit=50)

        # Simple keyword search for now
        # TODO: Use embeddings for semantic search
        query_lower = query.lower()
        relevant = []
        for msg in context:
            if query_lower in msg.get("message", "").lower():
                relevant.append(msg)

        if relevant:
            return {
                "success": True,
                "results": relevant[-5:],  # Last 5 matches
                "message": f"Found {len(relevant)} relevant memories"
            }
        return {
            "success": True,
            "results": [],
            "message": "No relevant memories found"
        }

    async def start(self):
        """Start the thinking engine background loop."""
        if not self.claude:
            print("WARNING: No ANTHROPIC_API_KEY - thinking engine disabled")
            return

        self.running = True
        asyncio.create_task(self._monitor_loop())
        print("Thinking engine started")

    async def stop(self):
        """Stop the thinking engine."""
        self.running = False

    async def process_user_input(self, text: str):
        """
        Process user input and decide on actions.

        Called by dashboard when user speaks or types.
        """
        if not text.strip():
            return

        self.last_user_input = text
        self._add_to_buffer("user", text)

        # Store in memory
        if self.memory_manager:
            await self.memory_manager.store_message(
                self.user_id, text, "user"
            )

        # Think about this input
        await self._think_and_act(text, source="user")

    async def _monitor_loop(self):
        """Background loop that polls Moshi output."""
        while self.running:
            try:
                # Get new text from Moshi
                new_text = self.voice_client.get_new_text()

                if new_text and new_text.strip():
                    self.last_moshi_output += new_text

                    # Check for sentence completion (simple heuristic)
                    if any(new_text.endswith(p) for p in ['.', '!', '?', '\n']):
                        # Process the accumulated output
                        output = self.last_moshi_output.strip()
                        if output:
                            self._add_to_buffer("moshi", output)

                            # Store in memory
                            if self.memory_manager:
                                await self.memory_manager.store_message(
                                    self.user_id, output, "assistant"
                                )

                            # Think about Moshi's response
                            await self._think_and_act(output, source="moshi")

                        self.last_moshi_output = ""

            except Exception as e:
                # Log but don't crash
                pass

            await asyncio.sleep(self.poll_interval)

    def _add_to_buffer(self, role: str, text: str):
        """Add message to conversation buffer."""
        self.conversation_buffer.append({
            "role": role,
            "content": text
        })
        # Keep buffer size limited
        if len(self.conversation_buffer) > self.max_buffer_size:
            self.conversation_buffer = self.conversation_buffer[-self.max_buffer_size:]

    async def _think_and_act(self, text: str, source: str):
        """
        Use Claude to decide what action to take, if any.

        Args:
            text: The text to analyze
            source: "user" or "moshi"
        """
        if not self.claude:
            return

        # Build context
        conversation = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in self.conversation_buffer[-10:]
        ])

        tool_descriptions = self.tool_registry.get_tool_descriptions()

        system_prompt = f"""You are a thinking engine that monitors conversations between a user and Moshi (a voice AI assistant).

Your job is to decide if any action should be taken based on the conversation.

{tool_descriptions}

Analyze the conversation and decide:
1. Should we search memory for relevant context to help Moshi? (e.g., user preferences, past conversations)
2. Should we execute a tool? (e.g., send email, make call)
3. Should we inject helpful context into Moshi's memory? (e.g., reminders, relevant info)

If action is needed, respond with a JSON object:
{{
    "action": "tool_call" | "inject_context" | "search_memory" | "none",
    "tool_name": "name of tool (if tool_call)",
    "tool_args": {{ ... }} (if tool_call),
    "context_to_inject": "text to inject into Moshi's context (if inject_context)",
    "memory_query": "what to search for (if search_memory)",
    "reasoning": "why this action"
}}

If no action needed, respond with:
{{
    "action": "none",
    "reasoning": "why no action needed"
}}

Be conservative - only act when clearly beneficial. Don't inject context unless it adds real value.
Don't search memory for every message - only when past context would genuinely help."""

        user_message = f"""Recent conversation:
{conversation}

New message from {source}:
"{text}"

What action, if any, should be taken?"""

        try:
            response = await self.claude.messages.create(
                model="claude-3-haiku-20240307",  # Fast, cheap for quick decisions
                max_tokens=500,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )

            # Parse response
            response_text = response.content[0].text

            # Extract JSON from response
            import json
            try:
                # Find JSON in response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    decision = json.loads(response_text[json_start:json_end])
                    await self._execute_decision(decision)
            except json.JSONDecodeError:
                pass  # No valid JSON, no action

        except Exception as e:
            # Log but don't crash
            pass

    async def _execute_decision(self, decision: Dict[str, Any]):
        """Execute the thinking engine's decision."""
        action = decision.get("action", "none")

        if action == "none":
            return

        elif action == "tool_call":
            tool_name = decision.get("tool_name")
            tool_args = decision.get("tool_args", {})

            if tool_name:
                result = await self.tool_registry.execute_tool(tool_name, tool_args)

                # Inject tool result into Moshi's context
                if result.get("success"):
                    result_text = str(result.get("result", ""))
                    self.voice_client.inject_tool_result(tool_name, result_text)

                    if self.on_tool_result:
                        self.on_tool_result(tool_name, result)

        elif action == "inject_context":
            context = decision.get("context_to_inject", "")
            if context:
                self.voice_client.inject_context(context)

                if self.on_injection:
                    self.on_injection(context)

        elif action == "search_memory":
            query = decision.get("memory_query", "")
            if query:
                result = await self._search_memory_handler(query)

                # If we found relevant memories, inject them
                if result.get("results"):
                    memories = result["results"]
                    memory_text = "\n".join([
                        f"[Past: {m.get('message', '')}]"
                        for m in memories
                    ])
                    self.voice_client.inject_context(
                        f"Relevant past context:\n{memory_text}"
                    )

                    if self.on_injection:
                        self.on_injection(memory_text)
