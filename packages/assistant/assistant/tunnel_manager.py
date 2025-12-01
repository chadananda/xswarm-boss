"""
TunnelManager - Two-tier tunneling system for webhook exposure.

Supports two providers:
- Cloudflare (FREE): Good for HTTP webhooks (email, SMS, OAuth)
- ngrok (PREMIUM): Required for WebSocket (Twilio voice)
"""

import subprocess
import time
import re
import os
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class TunnelProvider(Enum):
    """Tunnel provider selection."""
    CLOUDFLARE = "cloudflare"  # Free, HTTP only
    NGROK = "ngrok"            # Paid, WebSocket support


@dataclass
class TunnelInfo:
    """Information about an active tunnel."""
    public_url: str   # https://abc123.trycloudflare.com or https://abc123.ngrok.io
    ws_url: str       # wss://... (for WebSocket - only valid with ngrok)
    provider: TunnelProvider


class TunnelManager:
    """Manages tunnel lifecycle for local webhook exposure.

    Supports two providers:
    - cloudflare: Free, good for HTTP webhooks (email, SMS, OAuth)
    - ngrok: Paid, required for WebSocket (Twilio voice)

    Usage:
        # Free tier - Cloudflare for HTTP webhooks
        http_tunnel = TunnelManager(port=8787, provider=TunnelProvider.CLOUDFLARE)
        http_info = http_tunnel.start()
        print(f"HTTP: {http_info.public_url}")

        # Premium tier - ngrok for WebSocket
        voice_tunnel = TunnelManager(port=5000, provider=TunnelProvider.NGROK)
        voice_info = voice_tunnel.start()
        print(f"WSS: {voice_info.ws_url}")
    """

    def __init__(
        self,
        port: int,
        provider: TunnelProvider = TunnelProvider.CLOUDFLARE,
        auth_token: Optional[str] = None
    ):
        self.port = port
        self.provider = provider
        self.auth_token = auth_token
        self.process: Optional[subprocess.Popen] = None
        self.tunnel_info: Optional[TunnelInfo] = None

    def is_binary_available(self) -> bool:
        """Check if the required tunnel binary is available on PATH."""
        binary = "cloudflared" if self.provider == TunnelProvider.CLOUDFLARE else "ngrok"
        try:
            result = subprocess.run(
                ["which", binary],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def start(self) -> TunnelInfo:
        """Start tunnel and return public URL.

        Raises:
            RuntimeError: If tunnel binary not found or tunnel fails to start.
        """
        if not self.is_binary_available():
            binary = "cloudflared" if self.provider == TunnelProvider.CLOUDFLARE else "ngrok"
            install_hint = (
                "brew install cloudflare/cloudflare/cloudflared"
                if self.provider == TunnelProvider.CLOUDFLARE
                else "brew install ngrok && ngrok config add-authtoken <token>"
            )
            raise RuntimeError(f"{binary} not found. Install with: {install_hint}")

        if self.provider == TunnelProvider.NGROK:
            return self._start_ngrok()
        else:
            return self._start_cloudflare()

    def _start_cloudflare(self) -> TunnelInfo:
        """Start cloudflared quick tunnel (free, no account needed)."""
        # cloudflared tunnel --url http://localhost:PORT
        self.process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{self.port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Parse URL from cloudflared output
        # Example: "Your quick Tunnel has been created! Visit it at (and target machine/service): https://xxx.trycloudflare.com"
        # Or: "https://xxx.trycloudflare.com" on its own line
        for _ in range(30):
            if self.process.poll() is not None:
                # Process exited
                raise RuntimeError("cloudflared process exited unexpectedly")

            line = self.process.stdout.readline()
            if not line:
                time.sleep(1)
                continue

            if "trycloudflare.com" in line:
                match = re.search(r'https://[^\s]+\.trycloudflare\.com', line)
                if match:
                    url = match.group(0)
                    self.tunnel_info = TunnelInfo(
                        public_url=url,
                        ws_url=url.replace("https://", "wss://"),  # Won't work for WS, but set anyway
                        provider=TunnelProvider.CLOUDFLARE
                    )
                    return self.tunnel_info

            time.sleep(0.5)

        raise RuntimeError("Failed to start cloudflared tunnel (timeout)")

    def _start_ngrok(self) -> TunnelInfo:
        """Start ngrok tunnel (paid, WebSocket support)."""
        # Configure auth token if provided
        if self.auth_token:
            subprocess.run(
                ["ngrok", "config", "add-authtoken", self.auth_token],
                capture_output=True
            )

        # Start ngrok in background
        self.process = subprocess.Popen(
            ["ngrok", "http", str(self.port), "--log=stdout"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Poll ngrok API for tunnel URL
        # ngrok exposes an API at localhost:4040 when running
        import httpx

        for _ in range(30):
            if self.process.poll() is not None:
                raise RuntimeError("ngrok process exited unexpectedly")

            try:
                resp = httpx.get("http://localhost:4040/api/tunnels", timeout=1.0)
                data = resp.json()
                if data.get("tunnels"):
                    https_url = next(
                        (t["public_url"] for t in data["tunnels"]
                         if t["public_url"].startswith("https")),
                        None
                    )
                    if https_url:
                        self.tunnel_info = TunnelInfo(
                            public_url=https_url,
                            ws_url=https_url.replace("https://", "wss://"),
                            provider=TunnelProvider.NGROK
                        )
                        return self.tunnel_info
            except Exception:
                pass

            time.sleep(1)

        raise RuntimeError("Failed to start ngrok tunnel (timeout)")

    def stop(self):
        """Stop tunnel and cleanup."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
            except Exception:
                pass
            finally:
                self.process = None
                self.tunnel_info = None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False


def check_tunnel_binaries() -> dict:
    """Check which tunnel binaries are available.

    Returns:
        dict: {"cloudflared": bool, "ngrok": bool}
    """
    result = {}
    for binary in ["cloudflared", "ngrok"]:
        try:
            proc = subprocess.run(["which", binary], capture_output=True)
            result[binary] = proc.returncode == 0
        except Exception:
            result[binary] = False
    return result
