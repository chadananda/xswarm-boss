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

from .tools import ToolRegistry, Tool, ToolParameter, send_email_tool, make_call_tool
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

    async def process_scheduled_task(self, task_name: str, context: str):
        """
        Process a scheduled task trigger.
        
        Called by Scheduler when a task is due (e.g. email check).
        Decides if tools need to be run based on the task.
        """
        if not self.claude:
            return

        # We don't add this to the conversation buffer to avoid cluttering
        # the user-visible chat, but we do use it to trigger tool usage.
        
        system_prompt = f"""You are an autonomous AI assistant performing a scheduled background task: '{task_name}'.
        
        Your goal is to decide if any action is needed for this task.
        
        Available Tools:
        {self.tool_registry.get_tool_descriptions()}
        
        Task Context:
        {context}
        
        Decide:
        1. Should you run a tool? (e.g. check_email for 'email_check')
        2. If yes, which tool and what arguments?
        
        Respond with JSON:
        {{
            "action": "tool_call" | "none",
            "tool_name": "name",
            "tool_args": {{ ... }},
            "reasoning": "why"
        }}
        """
        
        try:
            response = await self.claude.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                system=system_prompt,
                messages=[{"role": "user", "content": "Perform scheduled check."}]
            )
            
            # Parse and execute
            import json
            response_text = response.content[0].text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0:
                decision = json.loads(response_text[json_start:json_end])
                await self._execute_decision(decision)
                
        except Exception as e:
            print(f"Error in scheduled task {task_name}: {e}")

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

    async def _summarize_for_moshi(self, data: str, context: str) -> str:
        """
        Use Sonnet 4.5 to create a terse summary for Moshi's small context window.

        Args:
            data: The raw data to summarize (memories, tool results, etc.)
            context: What this data is for (e.g., "memory search results", "email status")

        Returns:
            A very terse but accurate summary suitable for Moshi's ~3000 token context
        """
        if not self.claude:
            # Fallback: truncate to 200 chars
            return data[:200] + "..." if len(data) > 200 else data

        system_prompt = """You are a summarizer for a voice AI assistant with a VERY small context window (~3000 tokens total).

Your job is to create extremely terse but accurate summaries that capture the essential information.

Rules:
- Maximum 2-3 short sentences
- Use fragments, not full sentences where possible
- Focus on actionable/relevant facts only
- Omit pleasantries, timestamps, metadata
- Be direct: "User prefers X" not "The user has indicated a preference for X"
- Numbers and names are important - keep them
- If multiple items, pick the 2-3 most relevant

Example good summaries:
- "User prefers dark themes. Last set GLaDOS orange on Tuesday."
- "Email sent successfully to chad@example.com. Subject: Status Update"
- "User asked about weather twice yesterday. Likes detailed forecasts."

Example bad summaries (too verbose):
- "Based on the conversation history, it appears that the user has expressed a preference for..."
- "The email has been successfully dispatched to the intended recipient at the address..."
"""

        user_message = f"""Summarize this {context} for injection into Moshi's context:

{data}

Create a terse 2-3 sentence summary:"""

        try:
            response = await self.claude.messages.create(
                model="claude-sonnet-4-5-20250514",  # Sonnet 4.5 for smart summarization
                max_tokens=150,  # Force brevity
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            # Fallback: truncate
            return data[:200] + "..." if len(data) > 200 else data

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
                    result_data = result.get("result", {})

                    # Summarize the result for Moshi's small context
                    if isinstance(result_data, dict):
                        result_text = str(result_data)
                    else:
                        result_text = str(result_data)

                    summary = await self._summarize_for_moshi(
                        result_text,
                        f"tool '{tool_name}' result"
                    )
                    self.voice_client.inject_tool_result(tool_name, summary)

                    if self.on_tool_result:
                        self.on_tool_result(tool_name, result)

        elif action == "inject_context":
            context = decision.get("context_to_inject", "")
            if context:
                # Summarize if context is long
                if len(context) > 200:
                    context = await self._summarize_for_moshi(context, "context injection")

                self.voice_client.inject_context(context)

                if self.on_injection:
                    self.on_injection(context)

        elif action == "search_memory":
            query = decision.get("memory_query", "")
            if query:
                result = await self._search_memory_handler(query)

                # If we found relevant memories, summarize and inject them
                if result.get("results"):
                    memories = result["results"]

                    # Build raw memory text
                    raw_memories = "\n".join([
                        f"- {m.get('role', 'unknown')}: {m.get('message', '')}"
                        for m in memories
                    ])

                    # Summarize with Sonnet for Moshi's small context
                    summary = await self._summarize_for_moshi(
                        raw_memories,
                        f"memory search for '{query}'"
                    )

                    self.voice_client.inject_context(f"[Memory] {summary}")

                    if self.on_injection:
                        self.on_injection(summary)
