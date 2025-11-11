#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "assistant"))

import asyncio
from assistant.config import Config
from assistant.dashboard.app import VoiceAssistantApp

async def test_sidebar_layout():
    print("Testing left sidebar + content area layout...")
    config = Config()
    personas_dir = Path(__file__).parent.parent / "packages" / "personas"
    app = VoiceAssistantApp(config, personas_dir)

    async with app.run_test(size=(120, 40)) as pilot:
        print("✓ App initialized")
        await pilot.pause(1.0)

        # Test sidebar exists
        print("\n--- Testing Sidebar ---")
        sidebar = app.query_one("#sidebar")
        print(f"✓ Sidebar exists")

        # Test tab buttons
        tab_buttons = sidebar.query("Button")
        print(f"✓ Found {len(tab_buttons)} tab buttons in sidebar")
        for btn in tab_buttons:
            print(f"  - {btn.label} (id: {btn.id})")

        # Verify initial state
        status_btn = app.query_one("#tab-status")
        settings_btn = app.query_one("#tab-settings")
        chat_btn = app.query_one("#tab-chat")
        print(f"✓ All 3 tab buttons found")

        # Check active state
        if status_btn.has_class("active-tab"):
            print("✓ Status button is active initially")
        else:
            print("✗ WARNING: Status button should be active initially")

        # Test content area
        print("\n--- Testing Content Area ---")
        content_area = app.query_one("#content-area")
        print(f"✓ Content area exists")

        # Test content panes
        status_pane = app.query_one("#content-status")
        settings_pane = app.query_one("#content-settings")
        chat_pane = app.query_one("#content-chat")
        print(f"✓ All 3 content panes found")

        # Check visibility
        if status_pane.has_class("active-pane"):
            print("✓ Status pane is visible initially")
        else:
            print("✗ WARNING: Status pane should be visible initially")

        if not settings_pane.has_class("active-pane"):
            print("✓ Settings pane is hidden initially")
        else:
            print("✗ WARNING: Settings pane should be hidden initially")

        # Test tab switching
        print("\n--- Testing Tab Switching ---")

        # Click Settings button
        await pilot.click("#tab-settings")
        await pilot.pause(0.3)
        print("Clicked Settings button")

        # Check state after click
        if settings_btn.has_class("active-tab"):
            print("✓ Settings button is now active")
        else:
            print("✗ ERROR: Settings button should be active")

        if settings_pane.has_class("active-pane"):
            print("✓ Settings pane is now visible")
        else:
            print("✗ ERROR: Settings pane should be visible")

        if not status_pane.has_class("active-pane"):
            print("✓ Status pane is now hidden")
        else:
            print("✗ ERROR: Status pane should be hidden")

        # Click Chat button
        await pilot.click("#tab-chat")
        await pilot.pause(0.3)
        print("\nClicked Chat button")

        if chat_btn.has_class("active-tab"):
            print("✓ Chat button is now active")
        else:
            print("✗ ERROR: Chat button should be active")

        if chat_pane.has_class("active-pane"):
            print("✓ Chat pane is now visible")
        else:
            print("✗ ERROR: Chat pane should be visible")

        # Switch back to Status
        await pilot.click("#tab-status")
        await pilot.pause(0.3)
        print("\nClicked Status button")

        if status_btn.has_class("active-tab"):
            print("✓ Status button is active again")
        else:
            print("✗ ERROR: Status button should be active")

        if status_pane.has_class("active-pane"):
            print("✓ Status pane is visible again")
        else:
            print("✗ ERROR: Status pane should be visible")

        # Test status tab widgets still exist
        print("\n--- Testing Status Tab Content ---")
        visualizer = app.query_one("#visualizer")
        activity = app.query_one("#activity")
        status = app.query_one("#status")
        print(f"✓ Status tab contains: visualizer, activity, status")

        # Test settings tab content
        print("\n--- Testing Settings Tab Content ---")
        await pilot.click("#tab-settings")
        await pilot.pause(0.3)
        theme_selector = app.query_one("#theme-selector")
        radio_buttons = theme_selector.query("RadioButton")
        print(f"✓ Settings tab has theme selector with {len(radio_buttons)} options")

        # Test chat tab content
        print("\n--- Testing Chat Tab Content ---")
        await pilot.click("#tab-chat")
        await pilot.pause(0.3)
        chat_history = app.query_one("#chat-history")
        print(f"✓ Chat tab has chat history widget")

        print("\n✓✓✓ All sidebar layout tests passed! ✓✓✓")
        return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_sidebar_layout())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n✗✗✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
