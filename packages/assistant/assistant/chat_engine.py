"""
Chat Engine - AI conversation handler with persona and agenda injection.

This module provides text-based AI conversations when Moshi (voice) is not
available. It uses the connected Anthropic account (OAuth or API key) and
injects the active persona's system prompt and agenda.

Features:
- Persona system prompt injection (via message preamble for OAuth)
- Agenda/goal injection
- Visible thinking/reasoning in chat history
- Streaming responses
- Memory integration

IMPORTANT: OAuth tokens from Claude Code require the EXACT system prompt
"You are Claude Code, Anthropic's official CLI for Claude." - no additions.
Persona/agenda must be injected via a preamble in the first user message.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, AsyncGenerator, Callable
from enum import Enum

import httpx

from .auth import (
    AnthropicAuth,
    get_anthropic_client_headers,
    requires_system_prompt,
    ANTHROPIC_API_URL,
    CLAUDE_CODE_SYSTEM_PROMPT
)
from .personas.config import PersonaConfig
from .memory import PersistentChatHistory, EnhancedMemoryAgent, UserProfile
from .planner import PlannerData, PlanningSession
from .tools import set_planner_data, registry as tool_registry


# Default persona preamble for when no persona is set
DEFAULT_PERSONA_PREAMBLE = """<persona>
You are a helpful AI assistant. Be concise, accurate, and helpful.
</persona>"""


class MessageRole(Enum):
    """Chat message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    THINKING = "thinking"  # Internal reasoning (visible in UI)


@dataclass
class ChatMessage:
    """A single chat message."""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_api_message(self) -> Dict[str, str]:
        """Convert to Anthropic API message format."""
        # Thinking messages are not sent to API, only shown in UI
        if self.role == MessageRole.THINKING:
            return None
        return {
            "role": self.role.value if self.role != MessageRole.SYSTEM else "user",
            "content": self.content
        }


@dataclass
class ChatEngineConfig:
    """Configuration for the chat engine."""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.7
    show_thinking: bool = True  # Show reasoning in chat
    stream: bool = True  # Stream responses
    debug: bool = False  # Debug mode - shows persona preamble in gray


class ChatEngine:
    """
    AI conversation engine with persona and agenda injection.

    Handles text-based AI conversations when Moshi is not available.
    Uses the connected Anthropic account (OAuth or API key).

    Usage:
        auth = AnthropicAuth()
        persona = persona_manager.get_current_persona()

        engine = ChatEngine(auth, persona)

        async for chunk in engine.send_message("Hello!"):
            print(chunk, end="", flush=True)
    """

    def __init__(
        self,
        auth: AnthropicAuth,
        persona: Optional[PersonaConfig] = None,
        config: Optional[ChatEngineConfig] = None,
        on_thinking: Optional[Callable[[str], None]] = None,
        on_message: Optional[Callable[[str, str], None]] = None,
        on_system_prompt: Optional[Callable[[str], None]] = None,
        chat_history: Optional[PersistentChatHistory] = None,
        app_config: Optional[Any] = None
    ):
        """
        Initialize the chat engine.

        Args:
            auth: AnthropicAuth instance for API access
            persona: Active persona configuration (optional)
            config: Engine configuration (optional)
            on_thinking: Callback when thinking/reasoning occurs
            on_message: Callback when message is complete (role, content)
            on_system_prompt: Callback when persona preamble is injected (debug mode)
            chat_history: Persistent chat history for memory (optional)
            app_config: Main application Config with AI provider settings (optional)
        """
        self.auth = auth
        self.persona = persona
        self.config = config or ChatEngineConfig()
        self.app_config = app_config  # Main Config with local_ai_provider, ai_model, etc.
        self.on_thinking = on_thinking
        self.on_message = on_message
        self.on_system_prompt = on_system_prompt

        # Persistent chat history (memory)
        self.chat_history = chat_history

        # Memory agent for agentic recall with semantic search
        # Uses local CPU embeddings by default (no API key required)
        self.memory_agent: Optional[EnhancedMemoryAgent] = None
        if self.chat_history:
            persona_name = self.persona.name if self.persona else "default"
            self.memory_agent = EnhancedMemoryAgent(
                chat_history=self.chat_history,
                auth=self.auth,
                embedder=None,  # Will create local embedder automatically
                persona=persona_name
            )

        # Conversation history (in-memory for this session)
        self.messages: List[ChatMessage] = []

        # Agenda/goals for this session
        self.agenda: Optional[str] = None

        # Track if we've shown the persona preamble (only show once)
        self._preamble_shown = False

        # Pending recalled memories to inject
        self._pending_memory_context: Optional[str] = None

        # User profile for persistent facts (always in context)
        self.user_profile = UserProfile()

        # Planning system for daily planning and habit tracking
        self.planner = PlannerData()
        self.planning_session = PlanningSession(
            self.planner,
            user_name=self.user_profile.get_user_name()
        )
        # Wire up tools to use the same planner instance
        set_planner_data(self.planner)

        # Start persistent session if chat_history provided
        if self.chat_history:
            self.chat_history.start_session()

    def set_persona(self, persona: PersonaConfig) -> None:
        """Set or change the active persona."""
        self.persona = persona

    def set_agenda(self, agenda: str) -> None:
        """Set the current agenda/goals."""
        self.agenda = agenda

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.messages = []

    def end_session(self) -> None:
        """End the current session (saves to persistent storage)."""
        if self.chat_history:
            self.chat_history.end_session()

    def get_history(self) -> List[ChatMessage]:
        """Get conversation history."""
        return self.messages.copy()

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt.

        For OAuth tokens: Returns EXACT Claude Code prompt (required by API).
        For API keys: Returns full persona/agenda system prompt.
        """
        # OAuth tokens REQUIRE the exact Claude Code system prompt - no additions!
        if requires_system_prompt(self.auth):
            return CLAUDE_CODE_SYSTEM_PROMPT

        # For API keys, we can use a full system prompt
        parts = []

        # Add persona system prompt
        if self.persona:
            persona_prompt = self.persona.build_system_prompt(include_personality=True)
            if persona_prompt:
                parts.append(persona_prompt)
        else:
            parts.append("You are a helpful AI assistant. Be concise, accurate, and helpful.")

        # Add user profile (persistent facts about the user - always in context)
        if self.user_profile:
            user_context = self.user_profile.get_context_string()
            if user_context:
                parts.append(f"\n{user_context}")

        # Add planning context (daily planning, habits, tasks, etc.)
        if self.planning_session:
            planning_context = self.planning_session.get_planning_context()
            if planning_context:
                parts.append(f"\n{planning_context}")

        # Add memory context from previous sessions (automatic recall without search)
        if self.chat_history:
            memory_context = self.chat_history.get_context_for_injection()
            if memory_context:
                parts.append(f"\n{memory_context}")

        # Add agenda if set
        if self.agenda:
            parts.append(f"\n## Current Agenda\n{self.agenda}")

        # Add tools context
        tools_context = self._build_tools_context()
        if tools_context:
            parts.append(tools_context)

        # Add instructions for showing thinking
        if self.config.show_thinking:
            parts.append(
                "\n## Response Format\n"
                "Before answering, briefly share your reasoning process in a <thinking> block. "
                "This helps the user understand your approach. Keep thinking concise (1-3 sentences). "
                "Then provide your response.\n"
                "Example:\n"
                "<thinking>User is asking about X. I should consider Y and Z.</thinking>\n"
                "Here's my response..."
            )

        return "\n".join(parts)

    def _build_tools_context(self) -> str:
        """
        Build context about available tools and suggested integrations.

        This helps the AI understand what it can do and suggest missing capabilities.
        """
        lines = ["\n## Available Tools & Capabilities"]

        # Group tools by category
        tool_categories = {
            "Planning & Tasks": [],
            "Calendar & Schedule": [],
            "Habits & Goals": [],
            "Projects": [],
            "Ideas & Capture": [],
            "System": []
        }

        # Categorize tools
        for name, tool in tool_registry._tools.items():
            desc = tool.description if hasattr(tool, 'description') else ""
            entry = f"- {name}: {desc}"

            if any(k in name for k in ['task', 'commitment', 'planning', 'priority']):
                tool_categories["Planning & Tasks"].append(entry)
            elif any(k in name for k in ['calendar', 'event', 'schedule', 'meeting']):
                tool_categories["Calendar & Schedule"].append(entry)
            elif any(k in name for k in ['habit', 'streak']):
                tool_categories["Habits & Goals"].append(entry)
            elif 'project' in name:
                tool_categories["Projects"].append(entry)
            elif 'idea' in name:
                tool_categories["Ideas & Capture"].append(entry)
            else:
                tool_categories["System"].append(entry)

        # Add categorized tools
        for category, tools in tool_categories.items():
            if tools:
                lines.append(f"\n### {category}")
                lines.extend(tools)

        # Add suggested integrations
        lines.append("\n### Suggested Integrations (Not Yet Configured)")
        lines.append(
            "If the user asks about these, suggest they set them up in Settings > Integrations:"
        )
        lines.append("- Email: Read, search, draft, and send emails (requires email integration)")
        lines.append("- External Calendar: Sync with Google Calendar, Outlook (requires OAuth)")
        lines.append("- File Search: Index and search local files (enable in Settings)")
        lines.append("- Smart Home: Control lights, thermostat (requires Home Assistant)")
        lines.append("- Music: Control playback (requires Spotify/Apple Music)")

        lines.append("\n### Tool Usage")
        lines.append(
            "When the user requests an action you can perform, confirm what you're doing "
            "and report the result. For actions requiring missing integrations, explain "
            "what's needed and offer to help set it up."
        )

        return "\n".join(lines)

    def _build_persona_preamble(self) -> str:
        """
        Build persona/agenda preamble for OAuth mode.

        When using OAuth tokens, persona must be injected into the first
        user message because the system prompt must be exactly the
        Claude Code prompt.

        Includes memory context from recent sessions if available.
        """
        parts = []

        # Strong override instruction to adopt persona
        parts.append("IMPORTANT: For this conversation, you are role-playing as a specific character.")
        parts.append("Completely adopt the following persona and NEVER break character.")
        parts.append("Do NOT identify as Claude, Claude Code, or an AI assistant.")
        parts.append("Stay fully in character for all responses.\n")

        parts.append("<persona>")

        # Add persona
        if self.persona:
            persona_prompt = self.persona.build_system_prompt(include_personality=True)
            if persona_prompt:
                parts.append(persona_prompt)
            else:
                parts.append("You are a helpful AI assistant.")
        else:
            parts.append("You are a helpful AI assistant. Be concise, accurate, and helpful.")

        parts.append("</persona>")

        # Add user profile (persistent facts about the user - always in context)
        if self.user_profile:
            user_context = self.user_profile.get_context_string()
            if user_context:
                parts.append(f"\n{user_context}")

        # Add planning context (daily planning, habits, tasks, etc.)
        if self.planning_session:
            planning_context = self.planning_session.get_planning_context()
            if planning_context:
                parts.append(f"\n<planning>\n{planning_context}\n</planning>")

        # Add memory context from previous sessions
        if self.chat_history:
            memory_context = self.chat_history.get_context_for_injection()
            if memory_context:
                parts.append(f"\n{memory_context}")

        # Add agenda if set
        if self.agenda:
            parts.append(f"\n<agenda>\n{self.agenda}\n</agenda>")

        # Add thinking instructions
        if self.config.show_thinking:
            parts.append(
                "\n<instructions>\n"
                "Before answering, briefly share your reasoning in a <thinking> block. "
                "Keep it concise (1-3 sentences). Then provide your response.\n"
                "</instructions>"
            )

        return "\n".join(parts)

    def _prepare_api_messages(self) -> List[Dict[str, str]]:
        """
        Prepare messages for the API, injecting persona preamble and memory if needed.

        For OAuth: Injects persona preamble into first user message.
        For API keys: Returns messages as-is (persona is in system prompt).
        Also injects recalled memory context into the latest user message.
        """
        api_messages = []
        is_first_user_message = True
        last_user_msg_index = None

        # First pass: build messages and track last user message
        for i, msg in enumerate(self.messages):
            api_msg = msg.to_api_message()
            if not api_msg:
                continue

            # For OAuth, inject preamble into first user message
            if requires_system_prompt(self.auth) and msg.role == MessageRole.USER and is_first_user_message:
                preamble = self._build_persona_preamble()
                api_msg["content"] = f"{preamble}\n\nUser message: {api_msg['content']}"
                is_first_user_message = False

                # In debug mode, show the persona preamble (only once)
                if self.config.debug and self.on_system_prompt and not self._preamble_shown:
                    self.on_system_prompt(preamble)
                    self._preamble_shown = True

            if msg.role == MessageRole.USER:
                last_user_msg_index = len(api_messages)

            api_messages.append(api_msg)

        # Inject recalled memory context into the last user message
        if self._pending_memory_context and last_user_msg_index is not None:
            api_messages[last_user_msg_index]["content"] = (
                f"{self._pending_memory_context}\n\n{api_messages[last_user_msg_index]['content']}"
            )
            # Clear after use (only inject once)
            self._pending_memory_context = None

        return api_messages

    def _parse_thinking(self, content: str) -> tuple[Optional[str], str]:
        """
        Parse thinking blocks from response.

        Returns:
            Tuple of (thinking_text, main_response)
        """
        import re

        thinking_match = re.search(r'<thinking>(.*?)</thinking>', content, re.DOTALL)

        if thinking_match:
            thinking = thinking_match.group(1).strip()
            # Remove thinking block from main content
            main_content = re.sub(r'<thinking>.*?</thinking>\s*', '', content, flags=re.DOTALL)
            return thinking, main_content.strip()

        return None, content

    async def _stream_with_tools(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        request_body: dict,
        api_messages: list,
        max_tool_rounds: int = 5
    ) -> AsyncGenerator[str, None]:
        """
        Stream response with tool call handling.

        This method handles the full conversation flow including:
        1. Streaming the initial response
        2. Detecting tool_use blocks
        3. Executing tools
        4. Sending tool results back
        5. Streaming the final response

        Args:
            client: HTTP client
            headers: API headers
            request_body: Initial request body
            api_messages: Current conversation messages
            max_tool_rounds: Maximum tool call rounds to prevent infinite loops
        """
        import json

        current_messages = api_messages.copy()
        tool_round = 0

        while tool_round < max_tool_rounds:
            tool_round += 1

            # Update request with current messages
            request_body["messages"] = current_messages
            request_body["stream"] = True

            async with client.stream(
                "POST",
                f"{ANTHROPIC_API_URL}/v1/messages",
                headers=headers,
                json=request_body,
                timeout=120.0  # 2 min timeout for streaming
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_msg = f"API error: {error_text.decode()[:200]}"
                    self.messages.append(ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=error_msg
                    ))
                    yield error_msg
                    return

                # Track content blocks (text and tool_use)
                full_text = ""
                tool_calls = []
                current_tool_call = None
                current_tool_input = ""
                stop_reason = None

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            event = json.loads(data_str)
                            event_type = event.get("type", "")

                            if event_type == "message_start":
                                # Message started
                                pass

                            elif event_type == "content_block_start":
                                block = event.get("content_block", {})
                                if block.get("type") == "tool_use":
                                    current_tool_call = {
                                        "id": block.get("id"),
                                        "name": block.get("name"),
                                        "input": {}
                                    }
                                    current_tool_input = ""

                            elif event_type == "content_block_delta":
                                delta = event.get("delta", {})
                                delta_type = delta.get("type", "")

                                if delta_type == "text_delta":
                                    text = delta.get("text", "")
                                    full_text += text
                                    yield text

                                elif delta_type == "input_json_delta":
                                    # Tool input JSON streaming
                                    partial = delta.get("partial_json", "")
                                    current_tool_input += partial

                            elif event_type == "content_block_stop":
                                if current_tool_call:
                                    # Parse the accumulated JSON input
                                    try:
                                        current_tool_call["input"] = json.loads(current_tool_input) if current_tool_input else {}
                                    except json.JSONDecodeError:
                                        current_tool_call["input"] = {}
                                    tool_calls.append(current_tool_call)
                                    current_tool_call = None
                                    current_tool_input = ""

                            elif event_type == "message_delta":
                                delta = event.get("delta", {})
                                stop_reason = delta.get("stop_reason")

                        except json.JSONDecodeError:
                            pass

            # Process any text response
            if full_text:
                thinking, main_response = self._parse_thinking(full_text)

                if thinking and self.on_thinking:
                    self.messages.append(ChatMessage(
                        role=MessageRole.THINKING,
                        content=thinking
                    ))
                    self.on_thinking(thinking)

                # Only add assistant message if there's actual content
                if main_response.strip():
                    self.messages.append(ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=main_response
                    ))

                    if self.chat_history:
                        self.chat_history.add_message("assistant", main_response)

                    if self.on_message:
                        self.on_message("assistant", main_response)

            # If no tool calls, we're done
            if not tool_calls:
                return

            # Execute tool calls and prepare tool results
            yield "\n\n"  # Visual separator
            tool_results = []

            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_input = tool_call["input"]
                tool_id = tool_call["id"]

                # Show tool execution to user
                yield f"🔧 Executing: {tool_name}...\n"

                # Execute the tool
                result = await tool_registry.execute_tool(tool_name, tool_input)

                if result["success"]:
                    result_text = str(result["result"])
                    yield f"✓ {result_text}\n"
                else:
                    result_text = f"Error: {result['message']}"
                    yield f"✗ {result_text}\n"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result_text
                })

            yield "\n"

            # Build assistant message with tool_use blocks for API
            assistant_content = []
            if full_text:
                assistant_content.append({"type": "text", "text": full_text})
            for tc in tool_calls:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["input"]
                })

            # Add assistant message with tool calls to conversation
            current_messages.append({
                "role": "assistant",
                "content": assistant_content
            })

            # Add tool results as user message
            current_messages.append({
                "role": "user",
                "content": tool_results
            })

            # Continue loop to get next response with tool results

    async def send_message(
        self,
        user_message: str,
        stream: Optional[bool] = None
    ) -> AsyncGenerator[str, None]:
        """
        Send a message and get a streaming response.

        Args:
            user_message: The user's message
            stream: Override default streaming setting

        Yields:
            Response chunks as they arrive
        """
        should_stream = stream if stream is not None else self.config.stream

        # Add user message to history
        self.messages.append(ChatMessage(
            role=MessageRole.USER,
            content=user_message
        ))

        # Save to persistent history
        if self.chat_history:
            self.chat_history.add_message("user", user_message)

        # Extract facts from user message for persistent profile (async, uses configured AI)
        if self.user_profile:
            extracted_facts = await self.user_profile.extract_facts_from_message(
                user_message, auth=self.auth, config=self.app_config
            )
            for fact in extracted_facts:
                self.user_profile.add_fact(fact["category"], fact["fact"])

        # Trigger memory agent (async, non-blocking)
        if self.memory_agent:
            recalled = await self.memory_agent.on_message("user", user_message)
            if recalled:
                self._pending_memory_context = recalled

        # Get auth headers
        headers = get_anthropic_client_headers(self.auth)
        if not headers:
            error_msg = "Not authenticated. Please connect to Anthropic first."
            self.messages.append(ChatMessage(
                role=MessageRole.ASSISTANT,
                content=error_msg
            ))
            yield error_msg
            return

        # Build API messages with persona preamble if needed (for OAuth)
        api_messages = self._prepare_api_messages()

        # Build request
        request_body = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "system": self._build_system_prompt(),
            "messages": api_messages,
            "stream": should_stream
        }

        # Add tools to request
        tool_schemas = tool_registry.get_anthropic_tool_schemas()
        if tool_schemas:
            request_body["tools"] = tool_schemas

        if self.config.temperature != 1.0:
            request_body["temperature"] = self.config.temperature

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if should_stream:
                    # Streaming response with tool support
                    async for text_chunk in self._stream_with_tools(
                        client, headers, request_body, api_messages
                    ):
                        yield text_chunk
                else:
                    # Non-streaming response
                    response = await client.post(
                        f"{ANTHROPIC_API_URL}/v1/messages",
                        headers=headers,
                        json=request_body
                    )

                    if response.status_code != 200:
                        error_msg = f"API error: {response.text[:200]}"
                        self.messages.append(ChatMessage(
                            role=MessageRole.ASSISTANT,
                            content=error_msg
                        ))
                        yield error_msg
                        return

                    data = response.json()
                    content = data.get("content", [{}])[0].get("text", "")

                    # Parse thinking
                    thinking, main_response = self._parse_thinking(content)

                    if thinking and self.on_thinking:
                        self.messages.append(ChatMessage(
                            role=MessageRole.THINKING,
                            content=thinking
                        ))
                        self.on_thinking(thinking)

                    self.messages.append(ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=main_response
                    ))

                    # Save to persistent history
                    if self.chat_history:
                        self.chat_history.add_message("assistant", main_response)

                    if self.on_message:
                        self.on_message("assistant", main_response)

                    yield main_response

        except httpx.TimeoutException:
            error_msg = "Request timed out. Please try again."
            self.messages.append(ChatMessage(
                role=MessageRole.ASSISTANT,
                content=error_msg
            ))
            yield error_msg

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.messages.append(ChatMessage(
                role=MessageRole.ASSISTANT,
                content=error_msg
            ))
            yield error_msg

    async def send_message_simple(self, user_message: str) -> str:
        """
        Send a message and get the complete response (non-streaming).

        Args:
            user_message: The user's message

        Returns:
            Complete response text
        """
        response_parts = []
        async for chunk in self.send_message(user_message, stream=False):
            response_parts.append(chunk)
        return "".join(response_parts)


# Convenience function for quick chat
async def quick_chat(
    message: str,
    auth: Optional[AnthropicAuth] = None,
    persona: Optional[PersonaConfig] = None
) -> str:
    """
    Quick one-off chat message.

    Args:
        message: The message to send
        auth: Optional auth (uses default if not provided)
        persona: Optional persona

    Returns:
        Response text
    """
    if auth is None:
        auth = AnthropicAuth()

    engine = ChatEngine(auth, persona)
    return await engine.send_message_simple(message)
