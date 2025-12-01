"""
xSwarm Assistant - Developer-centric AI for managing multiple software projects.
"""

from importlib.metadata import version, PackageNotFoundError

# Lazy imports to avoid slow startup from heavy dependencies (openai, anthropic, torch)
# These are only imported when actually accessed
def __getattr__(name):
    if name == "Config":
        from .config import Config
        return Config
    elif name == "ChatEngine":
        from .chat_engine import ChatEngine
        return ChatEngine
    elif name == "ChatEngineConfig":
        from .chat_engine import ChatEngineConfig
        return ChatEngineConfig
    elif name == "ChatMessage":
        from .chat_engine import ChatMessage
        return ChatMessage
    elif name == "MessageRole":
        from .chat_engine import MessageRole
        return MessageRole
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

try:
    __version__ = version("voice-assistant")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["Config", "ChatEngine", "ChatEngineConfig", "ChatMessage", "MessageRole"]
