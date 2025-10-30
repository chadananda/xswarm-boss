"""
Entry point for python -m xswarm_voice.server
"""

import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())
