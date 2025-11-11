"""Pytest configuration and helpers for TUI testing with SVG analysis."""

import re
from pathlib import Path
from typing import Dict, List, Set, Any

def analyze_svg_snapshot(svg_path: Path) -> Dict[str, Any]:
    """
    Extract key information from SVG snapshot for programmatic verification.

    Args:
        svg_path: Path to SVG snapshot file

    Returns:
        Dictionary with:
            - colors: Set of hex colors found
            - text: List of text content
            - has_borders: Whether stroke attributes present
            - size: SVG viewBox dimensions
    """
    if not svg_path.exists():
        return {
            'colors': set(),
            'text': [],
            'has_borders': False,
            'size': None,
            'error': f'File not found: {svg_path}'
        }

    content = svg_path.read_text()

    return {
        'colors': extract_colors(content),
        'text': extract_text(content),
        'has_borders': 'stroke=' in content,
        'size': extract_size(content),
    }


def extract_colors(svg_content: str) -> Set[str]:
    """
    Extract all color values from SVG content.

    Finds colors in fill="#..." and stroke="#..." attributes.
    Returns uppercase hex values for consistent comparison.

    Args:
        svg_content: SVG file content as string

    Returns:
        Set of hex color strings (e.g., {'#00D4FF', '#FFA500'})
    """
    colors = set()

    # Find fill="..." and stroke="..." attributes
    for match in re.finditer(r'(?:fill|stroke)="(#[0-9a-fA-F]{6})"', svg_content):
        colors.add(match.group(1).upper())

    # Also check for rgb() format if used
    for match in re.finditer(r'(?:fill|stroke)="rgb\((\d+),\s*(\d+),\s*(\d+)\)"', svg_content):
        r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
        hex_color = f'#{r:02X}{g:02X}{b:02X}'
        colors.add(hex_color)

    return colors


def extract_text(svg_content: str) -> List[str]:
    """
    Extract all text content from SVG.

    Finds text within <text>...</text> and <tspan>...</tspan> elements.

    Args:
        svg_content: SVG file content as string

    Returns:
        List of text strings found in SVG
    """
    texts = []

    # Find <text>...</text> content
    for match in re.finditer(r'<text[^>]*>([^<]+)</text>', svg_content):
        text = match.group(1).strip()
        if text:
            texts.append(text)

    # Find <tspan>...</tspan> content (often used in Textual SVGs)
    for match in re.finditer(r'<tspan[^>]*>([^<]+)</tspan>', svg_content):
        text = match.group(1).strip()
        if text:
            texts.append(text)

    return texts


def extract_size(svg_content: str) -> tuple[int, int] | None:
    """
    Extract SVG viewBox dimensions.

    Args:
        svg_content: SVG file content as string

    Returns:
        (width, height) tuple or None if not found
    """
    match = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg_content)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return None


def verify_theme_colors(svg_path: Path, expected_colors: str | List[str]) -> bool:
    """
    Verify expected theme color(s) appear in SVG snapshot.

    Args:
        svg_path: Path to SVG snapshot file
        expected_colors: Single hex color string or list of hex colors
                        (e.g., "#00D4FF" or ["#00D4FF", "#FFA500"])

    Returns:
        True if all expected colors found in SVG, False otherwise
    """
    if not svg_path.exists():
        return False

    # Normalize to list
    if isinstance(expected_colors, str):
        expected_colors = [expected_colors]

    # Normalize to uppercase
    expected_colors = {color.upper() for color in expected_colors}

    analysis = analyze_svg_snapshot(svg_path)
    found_colors = analysis['colors']

    # Check if all expected colors are present
    return expected_colors.issubset(found_colors)


def verify_text_present(svg_path: Path, expected_texts: List[str]) -> bool:
    """
    Verify expected text content appears in SVG snapshot.

    Args:
        svg_path: Path to SVG snapshot file
        expected_texts: List of text strings that should appear

    Returns:
        True if all expected texts found in SVG, False otherwise
    """
    if not svg_path.exists():
        return False

    analysis = analyze_svg_snapshot(svg_path)
    svg_text_combined = ' '.join(analysis['text'])

    # Check if all expected texts are present
    return all(text in svg_text_combined for text in expected_texts)


def verify_layout_elements(svg_path: Path, expected_elements: List[str]) -> Dict[str, bool]:
    """
    Verify expected layout elements are present in SVG.

    Args:
        svg_path: Path to SVG snapshot file
        expected_elements: List of element indicators to check for
                          (e.g., ['border', 'panel', 'button'])

    Returns:
        Dictionary mapping element name to whether it was found
    """
    if not svg_path.exists():
        return {elem: False for elem in expected_elements}

    content = svg_path.read_text()

    results = {}
    for element in expected_elements:
        # Simple heuristic checks
        if element.lower() == 'border':
            results[element] = 'stroke=' in content
        elif element.lower() == 'panel':
            results[element] = '<rect' in content or '<path' in content
        elif element.lower() == 'button':
            # Buttons often have specific text or rect patterns
            results[element] = 'Button' in content or '<rect' in content
        else:
            # Generic check for element name in content
            results[element] = element in content

    return results


def color_similarity(color1: str, color2: str, tolerance: int = 15) -> bool:
    """
    Check if two hex colors are similar within tolerance.

    Useful for comparing colors that might have slight variations
    due to rendering or color adjustments.

    Args:
        color1: First hex color (e.g., "#00D4FF")
        color2: Second hex color (e.g., "#00D5FF")
        tolerance: Maximum difference per RGB channel (0-255)

    Returns:
        True if colors are within tolerance, False otherwise
    """
    # Remove # and convert to RGB
    def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)

    # Check if each channel is within tolerance
    return all(abs(c1 - c2) <= tolerance for c1, c2 in zip(rgb1, rgb2))


def get_dominant_colors(svg_path: Path, top_n: int = 5) -> List[tuple[str, int]]:
    """
    Get the most frequently used colors in SVG.

    Args:
        svg_path: Path to SVG snapshot file
        top_n: Number of top colors to return

    Returns:
        List of (color, count) tuples, sorted by frequency
    """
    if not svg_path.exists():
        return []

    content = svg_path.read_text()
    color_counts = {}

    # Count all color occurrences
    for match in re.finditer(r'(?:fill|stroke)="(#[0-9a-fA-F]{6})"', content):
        color = match.group(1).upper()
        color_counts[color] = color_counts.get(color, 0) + 1

    # Sort by count and return top N
    sorted_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_colors[:top_n]


# Example usage in tests:
#
# def test_theme_colors_present(snap_compare, tmp_path):
#     """Verify theme colors are applied correctly."""
#     app = VoiceAssistantApp()
#     assert snap_compare(app, terminal_size=(80, 30))
#
#     # Analyze the generated snapshot
#     svg_path = tmp_path / "__snapshots__" / "test_theme_colors_present.svg"
#     assert verify_theme_colors(svg_path, "#00D4FF")  # JARVIS cyan
#     assert verify_text_present(svg_path, ["Status", "Voice Assistant"])
#
# def test_layout_elements(snap_compare, tmp_path):
#     """Verify UI elements are rendered."""
#     app = VoiceAssistantApp()
#     assert snap_compare(app, terminal_size=(80, 30))
#
#     svg_path = tmp_path / "__snapshots__" / "test_layout_elements.svg"
#     elements = verify_layout_elements(svg_path, ['border', 'panel'])
#     assert all(elements.values()), f"Missing elements: {elements}"
