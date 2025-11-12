# Theme Switching Fix

## Problem

Theme switching was not working when selecting a theme in the Settings pane. When clicking on a theme RadioButton, the UI colors did not change.

## Root Cause

The code was incorrectly using `RadioButton.value` to store and retrieve the persona name. However, `RadioButton.value` is a **boolean** field (representing whether the button is pressed/selected), not a custom data field.

### Incorrect Code

```python
# Setting up RadioButtons (WRONG)
radio_btn = RadioButton(persona.name)
radio_btn.value = persona.name  # ❌ value is boolean, not string!

# Event handler (WRONG)
selected_persona_name = event.pressed.value  # ❌ Gets boolean, not string!
```

## Solution

Use `RadioButton.label.plain` to retrieve the persona name instead. The label contains the text we display (the persona name), and `.plain` gets the plain string from the Rich Text Content object.

### Corrected Code

```python
# Setting up RadioButtons (CORRECT)
radio_btn = RadioButton(persona.name)
radio_btn.id = f"theme-{persona.name.lower().replace(' ', '-')}"
# Note: RadioButton.value is boolean - we use label for data

# Event handler (CORRECT)
selected_persona_name = event.pressed.label.plain  # ✅ Gets "JARVIS", "GLaDOS", etc.
```

## Changes Made

### File: `assistant/dashboard/app.py`

1. **Line 295-296**: Removed incorrect `radio_btn.value = persona.name` assignment and added explanatory comment
2. **Line 352**: Changed from `event.pressed.value` to `event.pressed.label.plain` to get persona name
3. Removed debug logging that was added during investigation
4. Added comments explaining why we use `label` instead of `value`

## Testing

To test the fix:

1. Run the application: `python -m assistant.dashboard.app`
2. Click on the Settings tab
3. Select different themes (JARVIS, GLaDOS, HAL-9000, etc.)
4. Verify that:
   - Colors change immediately
   - Activity feed shows "🎨 Switching to [PersonaName] theme"
   - Border colors, text colors, and backgrounds all update
   - Visualizer border title updates to "xSwarm - [PersonaName]"

## Technical Details

### Textual RadioButton API

```python
class RadioButton:
    label: Content       # Rich text label (use .plain for string)
    value: bool          # Boolean pressed state (True/False)
    id: str | None       # Widget ID
```

### RadioSet.Changed Event

```python
class Changed:
    pressed: RadioButton  # The button that was pressed
    index: int            # Index of pressed button
    radio_set: RadioSet   # Parent RadioSet widget
```

## Related Files

- `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/assistant/assistant/dashboard/app.py` - Main application (fixed)
- `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/personas/*/theme.yaml` - Persona theme configurations

## Commit Message

```
fix: use RadioButton.label.plain instead of .value for theme selection

RadioButton.value is a boolean (pressed state), not for custom data.
Changed event handler to use event.pressed.label.plain to get the
persona name string. Theme switching now works correctly in Settings.

Fixes: Theme switching not working when clicking selection in settings
```
