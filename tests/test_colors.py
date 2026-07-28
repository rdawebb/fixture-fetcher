"""Tests for the colours module."""

import pytest

from utils.colors import (
    BUTTON_BG,
    MIN_CONTRAST,
    _contrast_ratio,
    is_legible,
    is_valid_hex,
    parse_club_colors,
    text_on,
)


class TestIsValidHex:
    """Tests for is_valid_hex function."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("#DA291C", True),
            ("#da291c", True),
            ("#FFF", False),
            ("DA291C", False),
            ("#GGGGGG", False),
            ("", False),
            (None, False),
            (123456, False),
        ],
    )
    def test_is_valid_hex(self, value, expected):
        """Test hex validation across well- and malformed values."""
        assert is_valid_hex(value) is expected


class TestContrast:
    """Tests for the contrast helpers."""

    def test_contrast_ratio_is_symmetric(self):
        """Test argument order does not change the ratio."""
        assert _contrast_ratio("#000000", "#ffffff") == pytest.approx(
            _contrast_ratio("#ffffff", "#000000")
        )

    def test_contrast_ratio_extremes(self):
        """Test black on white is 21:1 and a colour on itself is 1:1."""
        assert _contrast_ratio("#000000", "#ffffff") == pytest.approx(21, abs=0.01)
        assert _contrast_ratio("#123456", "#123456") == pytest.approx(1, abs=0.01)

    @pytest.mark.parametrize(
        "colour,expected",
        [
            ("#111111", True),
            ("#12224E", True),
            ("#FFFFFF", False),
            ("#6CABDD", False),
        ],
    )
    def test_is_legible(self, colour, expected):
        """Test legibility against the button background."""
        assert is_legible(colour) is expected


class TestParseClubColors:
    """Tests for parse_club_colors function."""

    @pytest.mark.parametrize(
        "club_colors,expected",
        [
            # First colour is dark enough, so it wins
            ("Red / White", "#D50000"),
            ("Claret / Blue", "#7A263A"),
            ("Black / White", "#111111"),
            # Multi-word colours must not collapse to their last word
            ("Sky Blue / Navy Blue", "#12224E"),
            ("Royal Blue / White", "#1B449C"),
            # White first, so the second colour is used instead
            ("White / Black", "#111111"),
            ("White / Blue / Yellow", "#0B4DA2"),
            # Case and spacing are normalised
            ("red/white", "#D50000"),
            ("  RED  /  WHITE  ", "#D50000"),
        ],
    )
    def test_parse_club_colors(self, club_colors, expected):
        """Test colours are mapped and the first legible one is chosen."""
        assert parse_club_colors(club_colors) == expected

    @pytest.mark.parametrize("club_colors", [None, "", "   ", "Turquoise / Beige"])
    def test_parse_club_colors_returns_none(self, club_colors):
        """Test unmappable input returns None so the CSS default applies."""
        assert parse_club_colors(club_colors) is None

    def test_all_colours_too_light_are_darkened(self):
        """Test an all-pale club gets a darkened accent rather than None."""
        result = parse_club_colors("White / Sky Blue")

        assert result is not None
        assert is_legible(result)
        # Darkened towards black from sky blue, not replaced by it
        assert result != "#6CABDD"

    def test_result_is_always_legible(self):
        """Test every returned colour clears the contrast threshold."""
        samples = [
            "Red / White",
            "White / Black",
            "Yellow / Green",
            "Gold / Black",
            "Sky Blue / White",
            "White / White",
        ]

        for club_colors in samples:
            colour = parse_club_colors(club_colors)
            assert colour is not None
            assert _contrast_ratio(colour, BUTTON_BG) >= MIN_CONTRAST

    def test_partially_unmapped_string(self):
        """Test unknown words are skipped rather than failing the whole string."""
        assert parse_club_colors("Turquoise / Red") == "#D50000"


class TestTextOn:
    """Tests for text_on function."""

    @pytest.mark.parametrize(
        "background,expected",
        [
            ("#111111", "#ffffff"),
            ("#12224E", "#ffffff"),
            ("#D50000", "#ffffff"),
            ("#FFFFFF", "#222222"),
            ("#C9A227", "#222222"),
        ],
    )
    def test_text_on(self, background, expected):
        """Test the foreground colour flips with background lightness."""
        assert text_on(background) == expected

    def test_text_on_picks_the_better_contrast(self):
        """Test the chosen foreground always beats the alternative."""
        for background in ["#111111", "#D50000", "#FFFFFF", "#C9A227", "#6CABDD"]:
            chosen = text_on(background)
            other = "#222222" if chosen == "#ffffff" else "#ffffff"

            assert _contrast_ratio(chosen, background) >= _contrast_ratio(
                other, background
            )
