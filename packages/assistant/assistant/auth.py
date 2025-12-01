"""
Anthropic API authentication with secure credential storage.

This module handles:
1. API key authentication for Anthropic API access
2. Claude Code Token Bridge - reuse OAuth tokens from Claude Code installation
3. Secure local credential storage (encrypted)
4. API key validation

The Claude Code Token Bridge allows users with Claude Pro/Max subscriptions
to use their subscription quota instead of paying per-token API rates.
"""

import base64
import hashlib
import json
import os
import socket
import subprocess
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Literal

import httpx


# Anthropic API endpoints
ANTHROPIC_API_URL = "https://api.anthropic.com"
ANTHROPIC_CONSOLE_URL = "https://console.anthropic.com/settings/keys"
ANTHROPIC_TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"

# Claude Code OAuth client ID (for token refresh)
CLAUDE_CODE_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"

# Required headers for OAuth-based API calls (matches Claude Code/OpenCode)
OAUTH_API_HEADERS = {
    "anthropic-version": "2023-06-01",
    "anthropic-beta": "claude-code-20250219,oauth-2025-04-20,interleaved-thinking-2025-05-14",
    "Content-Type": "application/json"
}

# Required system prompt for Claude Code OAuth tokens
# Without this, the API returns: "This credential is only authorized for use with Claude Code"
CLAUDE_CODE_SYSTEM_PROMPT = "You are Claude Code, Anthropic's official CLI for Claude."


@dataclass
class APIKeyInfo:
    """API key information with metadata."""
    api_key: str
    created_at: datetime
    validated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "api_key": self.api_key,
            "created_at": self.created_at.isoformat(),
            "validated_at": self.validated_at.isoformat() if self.validated_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "APIKeyInfo":
        """Deserialize from dictionary."""
        return cls(
            api_key=data["api_key"],
            created_at=datetime.fromisoformat(data["created_at"]),
            validated_at=datetime.fromisoformat(data["validated_at"]) if data.get("validated_at") else None
        )


@dataclass
class OAuthTokenInfo:
    """OAuth token information from Claude Code."""
    access_token: str
    refresh_token: str
    expires_at: datetime
    source: Literal["keychain", "file"] = "keychain"

    @property
    def is_expired(self) -> bool:
        """Check if the access token is expired (with 5 min buffer)."""
        return datetime.now() >= (self.expires_at - timedelta(minutes=5))

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat(),
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OAuthTokenInfo":
        """Deserialize from dictionary."""
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
            source=data.get("source", "keychain")
        )


class ClaudeCodeTokenBridge:
    """
    Bridge to read OAuth tokens from Claude Code installation.

    This allows users with Claude Pro/Max subscriptions to use their
    subscription quota instead of paying per-token API rates.

    On macOS, tokens are stored in:
    - Keychain Access (search "Claude Code")
    - Or ~/.claude/credentials.json (fallback)
    """

    KEYCHAIN_SERVICE = "Claude Code-credentials"
    CLAUDE_CREDENTIALS_PATH = Path.home() / ".claude" / "credentials.json"

    @classmethod
    def is_claude_code_installed(cls) -> bool:
        """Check if Claude Code is installed and has tokens."""
        # Check for keychain entry
        if cls._check_keychain_exists():
            return True
        # Check for credentials file
        if cls.CLAUDE_CREDENTIALS_PATH.exists():
            return True
        return False

    @classmethod
    def _check_keychain_exists(cls) -> bool:
        """Check if Claude Code keychain entry exists."""
        try:
            result = subprocess.run(
                [
                    "security", "find-generic-password",
                    "-s", cls.KEYCHAIN_SERVICE,
                ],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def read_tokens(cls) -> Optional[OAuthTokenInfo]:
        """
        Read OAuth tokens from Claude Code installation.

        Tries keychain first, then falls back to credentials file.

        Returns:
            OAuthTokenInfo if tokens found, None otherwise
        """
        # Try keychain first (more secure)
        tokens = cls._read_from_keychain()
        if tokens:
            return tokens

        # Fallback to credentials file
        tokens = cls._read_from_file()
        if tokens:
            return tokens

        return None

    @classmethod
    def _read_from_keychain(cls) -> Optional[OAuthTokenInfo]:
        """Read tokens from macOS Keychain."""
        try:
            result = subprocess.run(
                [
                    "security", "find-generic-password",
                    "-s", cls.KEYCHAIN_SERVICE,
                    "-w"  # Output password only
                ],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return None

            # Parse the JSON credentials
            creds = json.loads(result.stdout.strip())

            # Handle Claude Code keychain structure:
            # {"claudeAiOauth": {"accessToken": ..., "refreshToken": ..., "expiresAt": ...}}
            if "claudeAiOauth" in creds:
                oauth = creds["claudeAiOauth"]
                # Expires is in milliseconds
                expires_ms = oauth.get("expiresAt", 0)
                expires_at = datetime.fromtimestamp(expires_ms / 1000)

                return OAuthTokenInfo(
                    access_token=oauth["accessToken"],
                    refresh_token=oauth["refreshToken"],
                    expires_at=expires_at,
                    source="keychain"
                )

            # Fallback: older format {"anthropic": {"access": ..., "refresh": ..., "expires": ...}}
            if "anthropic" in creds:
                anthropic = creds["anthropic"]
                if anthropic.get("type") == "oauth":
                    expires_ms = anthropic.get("expires", 0)
                    expires_at = datetime.fromtimestamp(expires_ms / 1000)

                    return OAuthTokenInfo(
                        access_token=anthropic["access"],
                        refresh_token=anthropic["refresh"],
                        expires_at=expires_at,
                        source="keychain"
                    )

            return None
        except Exception:
            return None

    @classmethod
    def _read_from_file(cls) -> Optional[OAuthTokenInfo]:
        """Read tokens from Claude credentials file."""
        try:
            if not cls.CLAUDE_CREDENTIALS_PATH.exists():
                return None

            with open(cls.CLAUDE_CREDENTIALS_PATH) as f:
                creds = json.load(f)

            # Claude Code file structure:
            # {"claudeAiOauth": {"accessToken": ..., "refreshToken": ..., "expiresAt": ...}}
            if "claudeAiOauth" in creds:
                oauth = creds["claudeAiOauth"]
                expires_ms = oauth.get("expiresAt", 0)
                expires_at = datetime.fromtimestamp(expires_ms / 1000)

                return OAuthTokenInfo(
                    access_token=oauth["accessToken"],
                    refresh_token=oauth["refreshToken"],
                    expires_at=expires_at,
                    source="file"
                )

            # Fallback: older format
            if "anthropic" in creds:
                anthropic = creds["anthropic"]
                if anthropic.get("type") == "oauth":
                    expires_ms = anthropic.get("expires", 0)
                    expires_at = datetime.fromtimestamp(expires_ms / 1000)

                    return OAuthTokenInfo(
                        access_token=anthropic["access"],
                        refresh_token=anthropic["refresh"],
                        expires_at=expires_at,
                        source="file"
                    )

            return None
        except Exception:
            return None

    @classmethod
    def refresh_tokens(cls, refresh_token: str) -> Optional[OAuthTokenInfo]:
        """
        Refresh OAuth tokens using the refresh token.

        Args:
            refresh_token: The refresh token to use

        Returns:
            New OAuthTokenInfo if successful, None otherwise
        """
        try:
            with httpx.Client() as client:
                response = client.post(
                    ANTHROPIC_TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": CLAUDE_CODE_CLIENT_ID,
                        "refresh_token": refresh_token
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30
                )

                if response.status_code != 200:
                    return None

                data = response.json()
                expires_in = data.get("expires_in", 3600)
                expires_at = datetime.now() + timedelta(seconds=expires_in)

                return OAuthTokenInfo(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token", refresh_token),
                    expires_at=expires_at,
                    source="keychain"
                )
        except Exception:
            return None

    @classmethod
    def validate_token(cls, access_token: str) -> bool:
        """
        Validate an OAuth access token by making a test API call.

        Args:
            access_token: The access token to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            with httpx.Client() as client:
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    **OAUTH_API_HEADERS
                }
                response = client.post(
                    f"{ANTHROPIC_API_URL}/v1/messages",
                    headers=headers,
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "Hi"}]
                    },
                    timeout=10
                )
                # 200 = success, 400 = bad request (but token is valid)
                return response.status_code in (200, 400)
        except Exception:
            return False


class CredentialStorage:
    """
    Secure credential storage using file encryption.

    Credentials are encrypted using a machine-specific key derived from:
    - Machine ID / hardware UUID
    - User's home directory path

    This provides basic protection against credential theft if the file is copied
    to another machine, while being transparent to the user.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize credential storage.

        Args:
            storage_path: Custom path for credentials file. Defaults to ~/.config/xswarm/credentials.json
        """
        if storage_path is None:
            config_dir = Path.home() / ".config" / "xswarm"
            config_dir.mkdir(parents=True, exist_ok=True)
            storage_path = config_dir / "credentials.json"

        self.storage_path = storage_path
        self._encryption_key = self._derive_key()

    def _derive_key(self) -> bytes:
        """
        Derive an encryption key from machine-specific information.

        This provides basic protection - tokens encrypted on one machine
        cannot be easily decrypted on another.
        """
        # Gather machine-specific entropy
        machine_info = [
            str(Path.home()),  # User's home directory
            os.environ.get("USER", ""),
            os.environ.get("HOSTNAME", socket.gethostname()),
        ]

        # Try to get hardware UUID on macOS
        try:
            import subprocess
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "IOPlatformUUID" in result.stdout:
                for line in result.stdout.split("\n"):
                    if "IOPlatformUUID" in line:
                        uuid = line.split("=")[1].strip().strip('"')
                        machine_info.append(uuid)
                        break
        except Exception:
            pass  # Not on macOS or ioreg failed

        # Create a deterministic key from machine info
        key_material = "|".join(machine_info).encode()
        return hashlib.sha256(key_material).digest()

    def _encrypt(self, data: str) -> str:
        """Simple XOR encryption with the derived key."""
        data_bytes = data.encode()
        key_extended = (self._encryption_key * (len(data_bytes) // len(self._encryption_key) + 1))[:len(data_bytes)]
        encrypted = bytes(a ^ b for a, b in zip(data_bytes, key_extended))
        return base64.b64encode(encrypted).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt XOR encrypted data."""
        encrypted_bytes = base64.b64decode(encrypted_data)
        key_extended = (self._encryption_key * (len(encrypted_bytes) // len(self._encryption_key) + 1))[:len(encrypted_bytes)]
        decrypted = bytes(a ^ b for a, b in zip(encrypted_bytes, key_extended))
        return decrypted.decode()

    def save_api_key(self, provider: str, key_info: APIKeyInfo) -> None:
        """
        Save API key for a provider.

        Args:
            provider: Provider name (e.g., "anthropic")
            key_info: API key information to store
        """
        # Load existing credentials
        creds = self._load_all()

        # Add/update this provider's key
        creds[provider] = key_info.to_dict()

        # Encrypt and save
        encrypted = self._encrypt(json.dumps(creds))
        with open(self.storage_path, "w") as f:
            json.dump({"v": 1, "data": encrypted}, f)

    def load_api_key(self, provider: str) -> Optional[APIKeyInfo]:
        """
        Load API key for a provider.

        Args:
            provider: Provider name (e.g., "anthropic")

        Returns:
            APIKeyInfo if found, None otherwise
        """
        creds = self._load_all()
        if provider in creds:
            try:
                return APIKeyInfo.from_dict(creds[provider])
            except Exception:
                return None
        return None

    def delete_api_key(self, provider: str) -> None:
        """
        Delete API key for a provider.

        Args:
            provider: Provider name to delete
        """
        creds = self._load_all()
        if provider in creds:
            del creds[provider]
            encrypted = self._encrypt(json.dumps(creds))
            with open(self.storage_path, "w") as f:
                json.dump({"v": 1, "data": encrypted}, f)

    def _load_all(self) -> dict:
        """Load and decrypt all credentials."""
        if not self.storage_path.exists():
            return {}

        try:
            with open(self.storage_path) as f:
                stored = json.load(f)

            if "data" in stored:
                decrypted = self._decrypt(stored["data"])
                return json.loads(decrypted)
        except Exception:
            pass

        return {}


class AnthropicAuth:
    """
    Anthropic authentication handler supporting both API keys and Claude Code tokens.

    Supports two authentication methods:
    1. API Key: Standard pay-per-token access via ANTHROPIC_API_KEY
    2. Claude Code Token Bridge: Reuse OAuth tokens from Claude Code installation
       to access Claude Pro/Max subscription quota

    Usage:
        auth = AnthropicAuth()

        # Check for Claude Code tokens first (subscription access)
        if auth.has_claude_code_tokens():
            headers = auth.get_oauth_headers()
            # Use headers for API calls (Bearer token auth)

        # Or use API key (pay-per-token)
        elif auth.is_connected():
            api_key = auth.get_api_key()
            # Use api_key for API calls
    """

    def __init__(self, credential_storage: Optional[CredentialStorage] = None):
        """
        Initialize authentication handler.

        Args:
            credential_storage: Custom credential storage. Defaults to file-based storage.
        """
        self.credential_storage = credential_storage or CredentialStorage()
        self._cached_oauth_tokens: Optional[OAuthTokenInfo] = None

    # ==========================================================================
    # Claude Code Token Bridge Methods (Subscription Access)
    # ==========================================================================

    def has_claude_code_tokens(self) -> bool:
        """
        Check if Claude Code is installed and has valid OAuth tokens.

        Returns:
            True if Claude Code tokens are available
        """
        return ClaudeCodeTokenBridge.is_claude_code_installed()

    def get_oauth_tokens(self, refresh_if_expired: bool = True) -> Optional[OAuthTokenInfo]:
        """
        Get OAuth tokens from Claude Code installation.

        Args:
            refresh_if_expired: Whether to refresh tokens if expired

        Returns:
            OAuthTokenInfo if available, None otherwise
        """
        # Try cached tokens first
        if self._cached_oauth_tokens and not self._cached_oauth_tokens.is_expired:
            return self._cached_oauth_tokens

        # Read from Claude Code
        tokens = ClaudeCodeTokenBridge.read_tokens()
        if not tokens:
            return None

        # Refresh if expired
        if tokens.is_expired and refresh_if_expired:
            refreshed = ClaudeCodeTokenBridge.refresh_tokens(tokens.refresh_token)
            if refreshed:
                tokens = refreshed
            else:
                # Token refresh failed - tokens may be revoked
                return None

        self._cached_oauth_tokens = tokens
        return tokens

    def get_oauth_headers(self) -> Optional[dict]:
        """
        Get HTTP headers for OAuth-based API calls.

        Returns:
            Headers dict with Bearer token auth, or None if no tokens
        """
        tokens = self.get_oauth_tokens()
        if not tokens:
            return None

        return {
            "Authorization": f"Bearer {tokens.access_token}",
            **OAUTH_API_HEADERS
        }

    def get_auth_method(self) -> Literal["oauth", "api_key", "none"]:
        """
        Get the current authentication method available.

        Priority:
        1. OAuth (Claude Code tokens) - subscription access
        2. API key - pay-per-token
        3. None - not authenticated

        Returns:
            "oauth", "api_key", or "none"
        """
        if self.get_oauth_tokens():
            return "oauth"
        if self.get_api_key():
            return "api_key"
        return "none"

    def get_auth_status(self) -> dict:
        """
        Get detailed authentication status for display.

        Returns:
            Dict with auth info for UI display
        """
        method = self.get_auth_method()

        if method == "oauth":
            tokens = self.get_oauth_tokens()
            return {
                "method": "oauth",
                "connected": True,
                "label": "Claude Code (Subscription)",
                "detail": f"Token expires: {tokens.expires_at.strftime('%Y-%m-%d %H:%M')}" if tokens else "",
                "source": tokens.source if tokens else "unknown"
            }
        elif method == "api_key":
            return {
                "method": "api_key",
                "connected": True,
                "label": "API Key (Pay-per-token)",
                "detail": self.get_masked_key() or "",
                "source": "stored"
            }
        else:
            has_cc = ClaudeCodeTokenBridge.is_claude_code_installed()
            return {
                "method": "none",
                "connected": False,
                "label": "Not Connected",
                "detail": "Claude Code detected but tokens invalid" if has_cc else "No auth configured",
                "source": None
            }

    # ==========================================================================
    # API Key Methods (Pay-per-token Access)
    # ==========================================================================

    def get_api_key(self) -> Optional[str]:
        """
        Get the stored API key.

        Returns:
            API key string if stored, None otherwise
        """
        key_info = self.credential_storage.load_api_key("anthropic")
        if key_info:
            return key_info.api_key
        return None

    def save_api_key(self, api_key: str, validate: bool = True) -> bool:
        """
        Save an API key after optional validation.

        Args:
            api_key: The API key to save (should start with 'sk-ant-')
            validate: Whether to validate the key before saving

        Returns:
            True if saved successfully, False if validation failed
        """
        # Basic format check
        if not api_key or not api_key.startswith("sk-ant-"):
            return False

        if validate:
            if not self.validate_api_key(api_key):
                return False

        key_info = APIKeyInfo(
            api_key=api_key,
            created_at=datetime.now(),
            validated_at=datetime.now() if validate else None
        )
        self.credential_storage.save_api_key("anthropic", key_info)
        return True

    def validate_api_key(self, api_key: str) -> bool:
        """
        Validate an API key by making a test request to Anthropic API.

        Args:
            api_key: The API key to validate

        Returns:
            True if the key is valid, False otherwise
        """
        try:
            with httpx.Client() as client:
                # Use the messages endpoint with a minimal request
                response = client.post(
                    f"{ANTHROPIC_API_URL}/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "Hi"}]
                    },
                    timeout=10
                )
                # 200 = success, 400 = bad request (but key is valid)
                # 401 = invalid key, 403 = forbidden
                return response.status_code in (200, 400)
        except Exception:
            return False

    def disconnect(self) -> None:
        """
        Disconnect by removing stored API key.
        Note: This does not affect Claude Code tokens.
        """
        self.credential_storage.delete_api_key("anthropic")
        self._cached_oauth_tokens = None

    def is_connected(self) -> bool:
        """
        Check if we have any valid authentication (OAuth or API key).

        Returns:
            True if authenticated via either method
        """
        return self.get_auth_method() != "none"

    def open_api_key_page(self) -> None:
        """
        Open the Anthropic console API keys page in the browser.
        """
        webbrowser.open(ANTHROPIC_CONSOLE_URL)

    def get_masked_key(self) -> Optional[str]:
        """
        Get a masked version of the API key for display.

        Returns:
            Masked key like 'sk-ant-...xxxx' or None if no key stored
        """
        key = self.get_api_key()
        if key and len(key) > 12:
            return f"{key[:7]}...{key[-4:]}"
        return None


# Backwards compatibility aliases
TokenStorage = CredentialStorage
AnthropicOAuth = AnthropicAuth
TokenInfo = OAuthTokenInfo  # Legacy alias


def get_anthropic_client_headers(auth: AnthropicAuth) -> Optional[dict]:
    """
    Get the appropriate headers for Anthropic API calls based on available auth.

    This is a convenience function that returns the correct headers
    for either OAuth or API key authentication.

    IMPORTANT: When using OAuth tokens, you MUST include the Claude Code
    system prompt in your API request body. Use get_oauth_system_prompt()
    or the CLAUDE_CODE_SYSTEM_PROMPT constant.

    Args:
        auth: AnthropicAuth instance

    Returns:
        Headers dict for API calls, or None if not authenticated
    """
    method = auth.get_auth_method()

    if method == "oauth":
        return auth.get_oauth_headers()
    elif method == "api_key":
        api_key = auth.get_api_key()
        if api_key:
            return {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
    return None


def get_oauth_system_prompt() -> str:
    """
    Get the required system prompt for Claude Code OAuth tokens.

    When using OAuth tokens from Claude Code, the API requires this
    system prompt to be included in the request. Without it, the API
    returns: "This credential is only authorized for use with Claude Code"

    Returns:
        The required system prompt string
    """
    return CLAUDE_CODE_SYSTEM_PROMPT


def requires_system_prompt(auth: AnthropicAuth) -> bool:
    """
    Check if the current auth method requires the Claude Code system prompt.

    Args:
        auth: AnthropicAuth instance

    Returns:
        True if OAuth auth (requires system prompt), False for API key
    """
    return auth.get_auth_method() == "oauth"
