"""Tests for the text module."""

import pytest

from utils.text import slugify


class TestSlugify:
    """Tests for slugify function."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("Arsenal", "arsenal"),
            ("Man Utd", "man-utd"),
            ("AFC Bournemouth", "afc-bournemouth"),
            ("Brighton & Hove Albion FC", "brighton---hove-albion-fc"),
            ("Premier League", "premier-league"),
            ("PL", "pl"),
            ("", ""),
            ("---", ""),
            ("Nott'm Forest", "nott-m-forest"),
        ],
    )
    def test_slugify(self, input_name, expected):
        """Test slugification of club and competition names."""
        assert slugify(input_name) == expected
