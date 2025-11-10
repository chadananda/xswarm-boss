#!/usr/bin/env python3
"""Quick test to verify TUI widgets render without errors"""

import sys
sys.path.insert(0, '.')

from assistant.dashboard.widgets.status import StatusWidget
from assistant.dashboard.widgets.activity_feed import ActivityFeed
from assistant.dashboard.widgets.header import CyberpunkHeader
from assistant.dashboard.widgets.footer import CyberpunkFooter

print("Testing widget imports... OK")

# Test that widgets can create instances
try:
    status = StatusWidget()
    print("StatusWidget instantiation... OK")

    activity = ActivityFeed()
    print("ActivityFeed instantiation... OK")

    header = CyberpunkHeader()
    print("CyberpunkHeader instantiation... OK")

    footer = CyberpunkFooter()
    print("CyberpunkFooter instantiation... OK")

    print("\nAll widgets instantiate successfully!")
    print("\nNow try running the full TUI:")
    print("  python3 -m assistant.main")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
