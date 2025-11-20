import sys
import os
from pathlib import Path

# Add packages/assistant to path
sys.path.insert(0, str(Path.cwd() / "packages" / "assistant"))

try:
    print("Attempting to import assistant.voice_server...")
    import assistant.voice_server
    print("Import successful.")
    print(f"Dir: {dir(assistant.voice_server)}")
    
    print("Attempting to import start_voice_server...")
    from assistant.voice_server import start_voice_server
    print("Import successful.")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
