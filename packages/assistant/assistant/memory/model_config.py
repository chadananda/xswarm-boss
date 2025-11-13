"""
Model configuration parser for thinking service.
Parses PROVIDER:model-name format from .env files (dev mode only).
"""
# Standard library imports
import os
from dataclasses import dataclass
from typing import List, Optional, Dict
from pathlib import Path
# Load dotenv for .env file support
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional


@dataclass
class ModelConfig:
    """
    Configuration for a thinking model.

    Attributes:
        provider: Model provider (ANTHROPIC, OPENAI, OLLAMA)
        model: Model identifier (e.g., "claude-haiku-4-5", "gpt-4-turbo")
    """
    provider: str
    model: str

    @classmethod
    def parse(cls, config_string: str) -> "ModelConfig":
        """
        Parse a single model configuration string.

        Format: PROVIDER:model-name

        Examples:
            >>> ModelConfig.parse("ANTHROPIC:claude-haiku-4-5")
            ModelConfig(provider='ANTHROPIC', model='claude-haiku-4-5')

            >>> ModelConfig.parse("OLLAMA:llama3.2:3b")
            ModelConfig(provider='OLLAMA', model='llama3.2:3b')

        Args:
            config_string: Configuration in PROVIDER:model format

        Returns:
            ModelConfig instance

        Raises:
            ValueError: If format is invalid or missing components
        """
        if not config_string or not isinstance(config_string, str):
            raise ValueError("config_string must be a non-empty string")
        # Strip whitespace and quotes
        config_string = config_string.strip().strip('"').strip("'")
        # Split on first colon only (models may have colons like llama3.2:3b)
        if ":" not in config_string:
            raise ValueError(
                f"Invalid model config format: '{config_string}'. "
                f"Expected format: PROVIDER:model-name"
            )
        # Split on first colon, preserve rest
        parts = config_string.split(":", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid model config format: '{config_string}'. "
                f"Expected format: PROVIDER:model-name"
            )
        provider, model = parts
        # Validate components
        provider = provider.strip().upper()
        model = model.strip()
        if not provider:
            raise ValueError("Provider cannot be empty")
        if not model:
            raise ValueError("Model name cannot be empty")
        # Validate provider is recognized
        valid_providers = {"ANTHROPIC", "OPENAI", "OLLAMA"}
        if provider not in valid_providers:
            raise ValueError(
                f"Unknown provider: '{provider}'. "
                f"Valid providers: {', '.join(sorted(valid_providers))}"
            )
        return cls(provider=provider, model=model)

    @classmethod
    def parse_list(cls, config_string: str) -> List["ModelConfig"]:
        """
        Parse a comma-separated list of model configurations.
        Used for fallback chains.

        Example:
            >>> ModelConfig.parse_list("OLLAMA:llama3.2:3b,ANTHROPIC:claude-haiku-4-5")
            [ModelConfig(provider='OLLAMA', model='llama3.2:3b'),
             ModelConfig(provider='ANTHROPIC', model='claude-haiku-4-5')]

        Args:
            config_string: Comma-separated list of PROVIDER:model configs

        Returns:
            List of ModelConfig instances

        Raises:
            ValueError: If any config is invalid
        """
        if not config_string or not isinstance(config_string, str):
            raise ValueError("config_string must be a non-empty string")
        # Strip and split on commas
        config_string = config_string.strip()
        configs = []
        for config in config_string.split(","):
            config = config.strip()
            if config:  # Skip empty strings
                configs.append(cls.parse(config))
        if not configs:
            raise ValueError("No valid configurations found in list")
        return configs

    def __str__(self) -> str:
        """String representation"""
        return f"{self.provider}:{self.model}"

    def __repr__(self) -> str:
        """Developer representation"""
        return f"ModelConfig(provider='{self.provider}', model='{self.model}')"


def load_thinking_config(debug_mode: bool = False) -> Optional[Dict[str, ModelConfig]]:
    """
    Load thinking engine configuration from environment variables.
    Only loads in debug/dev mode. Returns None in production.

    Environment variables:
        THINKING_ENGINE_LIGHT: Fast, cheap model for simple tasks
        THINKING_ENGINE_NORMAL: Balanced model for standard tasks
        THINKING_ENGINE_DEEP: Advanced model for complex reasoning

    Example .env:
        THINKING_ENGINE_LIGHT="ANTHROPIC:claude-haiku-4-5"
        THINKING_ENGINE_NORMAL="OPENAI:gpt-4-turbo"
        THINKING_ENGINE_DEEP="ANTHROPIC:sonnet-4-5"

    Args:
        debug_mode: If True, loads from .env. If False, returns None.

    Returns:
        Dict mapping thinking levels to ModelConfig, or None if not debug mode.
        Keys: "light", "normal", "deep"

    Raises:
        ValueError: If debug_mode=True but configs are invalid
    """
    if not debug_mode:
        return None
    # Default configurations (fallback if env vars not set)
    defaults = {
        "light": "ANTHROPIC:claude-haiku-4-5",
        "normal": "ANTHROPIC:sonnet-4-5",
        "deep": "ANTHROPIC:sonnet-4-5"
    }
    # Environment variable names
    env_vars = {
        "light": "THINKING_ENGINE_LIGHT",
        "normal": "THINKING_ENGINE_NORMAL",
        "deep": "THINKING_ENGINE_DEEP"
    }
    # Build config dict
    config = {}
    for level, env_var in env_vars.items():
        # Get from env or use default
        config_string = os.getenv(env_var)
        if not config_string:
            # Use default
            config_string = defaults[level]
            # Optional: Log warning if env var not set
            # print(f"Warning: {env_var} not set, using default: {config_string}")
        # Parse configuration
        try:
            config[level] = ModelConfig.parse(config_string)
        except ValueError as e:
            raise ValueError(
                f"Invalid configuration for {env_var}: {e}"
            ) from e
    return config


# Convenience function for getting single config
def get_thinking_model(level: str = "normal", debug_mode: bool = False) -> Optional[ModelConfig]:
    """
    Get thinking model configuration for a specific level.

    Args:
        level: Thinking level ("light", "normal", or "deep")
        debug_mode: If True, loads from .env. If False, returns None.

    Returns:
        ModelConfig for the requested level, or None if not debug mode

    Raises:
        ValueError: If level is invalid or config is malformed
    """
    valid_levels = {"light", "normal", "deep"}
    if level not in valid_levels:
        raise ValueError(
            f"Invalid thinking level: '{level}'. "
            f"Valid levels: {', '.join(sorted(valid_levels))}"
        )
    config = load_thinking_config(debug_mode=debug_mode)
    if config is None:
        return None
    return config[level]
