"""Derive accent colours from the API's free-text club colours.

football-data.org reports club colours as words rather than hex values
("Red / White", "Claret / Blue", "Sky Blue / White"), so they have to be mapped
before the site can use them. Many clubs list a pale colour first, which is
unusable as button text or behind white hover text, so the chosen accent is
always checked for contrast before it is returned.
"""

from __future__ import annotations

import re

HEX_COLOUR = re.compile(r"^#[0-9a-fA-F]{6}$")

# Background the accent is used as text against (`.competitions-list button`)
BUTTON_BG = "#f0f0f0"

# Minimum contrast ratio for normal text (WCAG AA)
MIN_CONTRAST = 4.5

# Warm colours are pitched deliberately dark: at their natural brightness they
# fail the contrast check and fall through to the club's second colour, which
# loses the hue entirely (gold-and-black clubs would all render plain black).
COLOUR_WORDS: dict[str, str] = {
    "amber": "#96570A",
    "black": "#111111",
    "blue": "#0B4DA2",
    "burgundy": "#6E1B32",
    "cherry": "#A31F34",
    "claret": "#7A263A",
    "gold": "#7A6000",
    "gray": "#4A4A4A",
    "green": "#0B6E3A",
    "grey": "#4A4A4A",
    "light blue": "#6CABDD",
    "maroon": "#6E2639",
    "navy blue": "#12224E",
    "navy": "#12224E",
    "orange": "#A0522D",
    "pink": "#C2185B",
    "purple": "#5B2D8E",
    "red": "#D50000",
    "royal blue": "#1B449C",
    "silver": "#9A9A9A",
    "sky blue": "#6CABDD",
    "tangerine": "#A0522D",
    "white": "#FFFFFF",
    "yellow": "#C9A227",
}


def is_valid_hex(value: object) -> bool:
    """Check a value is a #RRGGBB colour string.

    Args:
        value: Candidate colour, from a hand-edited YAML file so any type.

    Returns:
        True if the value is a well-formed #RRGGBB string.
    """
    return isinstance(value, str) and bool(HEX_COLOUR.match(value))


def is_legible(hex_colour: str, background: str = BUTTON_BG) -> bool:
    """Check a colour meets the minimum contrast to be used as text.

    Args:
        hex_colour: Colour in #RRGGBB form.
        background: Colour it will be rendered against.

    Returns:
        True if the contrast ratio is at least 4.5:1 (WCAG AA, normal text).
    """
    return _contrast_ratio(hex_colour, background) >= MIN_CONTRAST


def _to_rgb(hex_colour: str) -> tuple[int, int, int]:
    """Split a #RRGGBB string into its red, green and blue components.

    Args:
        hex_colour: Colour in #RRGGBB form.

    Returns:
        Tuple of red, green and blue values in the range 0-255.
    """
    value = hex_colour.lstrip("#")

    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _relative_luminance(hex_colour: str) -> float:
    """Calculate the WCAG relative luminance of a colour.

    Args:
        hex_colour: Colour in #RRGGBB form.

    Returns:
        Relative luminance between 0 (black) and 1 (white).
    """
    channels = []
    for channel in _to_rgb(hex_colour):
        c = channel / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)

    r, g, b = channels

    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(a: str, b: str) -> float:
    """Calculate the WCAG contrast ratio between two colours.

    Args:
        a: First colour in #RRGGBB form.
        b: Second colour in #RRGGBB form.

    Returns:
        Contrast ratio between 1 (identical) and 21 (black on white).
    """
    darker, lighter = sorted((_relative_luminance(a), _relative_luminance(b)))

    return (lighter + 0.05) / (darker + 0.05)


def _darken(hex_colour: str, background: str = BUTTON_BG) -> str:
    """Darken a colour until it meets the minimum contrast against a background.

    Args:
        hex_colour: Colour in #RRGGBB form.
        background: Colour the result must be legible against.

    Returns:
        The darkened colour in #RRGGBB form, at worst black.
    """
    r, g, b = _to_rgb(hex_colour)

    # Scale towards black in small steps so the hue is preserved
    for step in range(20):
        factor = 1 - (step * 0.05)
        candidate = (
            f"#{round(r * factor):02X}{round(g * factor):02X}{round(b * factor):02X}"
        )
        if is_legible(candidate, background):
            return candidate

    return "#000000"


def parse_club_colors(club_colors: str | None) -> str | None:
    """Pick a legible accent colour from a club colours string.

    Args:
        club_colors: The API's clubColors string, e.g. "Claret / Blue".

    Returns:
        A #RRGGBB colour with sufficient contrast to be used as button text, or
        None if no colour in the string could be mapped.
    """
    if not club_colors:
        return None

    mapped = []
    for token in club_colors.split("/"):
        token = " ".join(token.lower().split())
        if not token:
            continue

        # Match the full token first so "sky blue" doesn't collapse to "blue"
        colour = COLOUR_WORDS.get(token) or COLOUR_WORDS.get(token.split()[-1])
        if colour:
            mapped.append(colour)

    if not mapped:
        return None

    # Prefer the first colour dark enough to read, so white-shirt clubs fall
    # through to their second colour rather than becoming invisible
    for colour in mapped:
        if is_legible(colour):
            return colour

    return _darken(mapped[0])


def text_on(hex_colour: str) -> str:
    """Pick a foreground colour that reads against a given background.

    Args:
        hex_colour: Background colour in #RRGGBB form.

    Returns:
        "#ffffff" or "#222222", whichever contrasts better.
    """
    on_light = _contrast_ratio("#222222", hex_colour)
    on_dark = _contrast_ratio("#ffffff", hex_colour)

    return "#ffffff" if on_dark >= on_light else "#222222"
