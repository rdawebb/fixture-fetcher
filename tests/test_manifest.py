"""Tests for the manifest module."""

import json
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from utils.manifest import (
    _get_competition_name,
    _unslug,
    generate_manifest,
    load_color_overrides,
)


def _ics(*events: tuple[datetime, str | None]) -> str:
    """Build an ICS document from (start, status) pairs.

    Args:
        events: Each event's start time and optional STATUS value.

    Returns:
        The ICS document as text.
    """
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//test//EN"]

    for index, (start, status) in enumerate(events):
        lines += [
            "BEGIN:VEVENT",
            f"UID:{index}@test",
            "DTSTAMP:20260101T000000Z",
            f"DTSTART:{start.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}",
            "SUMMARY:Test Match",
        ]
        if status:
            lines.append(f"STATUS:{status}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    return "\n".join(lines) + "\n"


def _team_from(manifest_file) -> dict:
    """Read the single team entry out of a written manifest.

    Args:
        manifest_file: Path to the manifest JSON file.

    Returns:
        The first team entry of the first league.
    """
    with open(manifest_file) as f:
        return json.load(f)["calendars"][0]["teams"][0]


class TestUnslug:
    """Tests for _unslug function."""

    @pytest.mark.parametrize(
        "input_slug,uppercase,expected",
        [
            ("premier", False, "Premier"),
            ("premier-league", False, "Premier League"),
            ("fa-cup-championship", False, "Fa Cup Championship"),
            ("premier-league", True, "PREMIER LEAGUE"),
            ("pl", True, "PL"),
            ("", False, ""),
            ("PL", False, "Pl"),
            ("championship-2-division", False, "Championship 2 Division"),
        ],
    )
    def test_unslug(self, input_slug, uppercase, expected):
        """Test _unslug function with various inputs."""
        result = _unslug(input_slug, uppercase=uppercase)
        assert result == expected


class TestGetCompetitionName:
    """Tests for _get_competition_name function."""

    @pytest.mark.parametrize(
        "code,expected",
        [
            ("PL", "Premier League"),
            ("UNKNOWN", "UNKNOWN"),
            ("pl", "pl"),
            ("", ""),
            ("FA-CUP", "FA-CUP"),
        ],
    )
    def test_get_competition_name(self, code, expected):
        """Test getting competition names from codes."""
        assert _get_competition_name(code) == expected


class TestGenerateManifest:
    """Tests for generate_manifest function."""

    def test_generate_manifest_creates_file(self, calendars_with_single_team, tmp_path):
        """Test that generate_manifest creates a JSON file."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        assert output_file.exists()

    def test_generate_manifest_creates_valid_json(
        self, calendars_with_single_team, tmp_path
    ):
        """Test that generated manifest is valid JSON."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        with open(output_file) as f:
            manifest = json.load(f)

        assert isinstance(manifest, dict)
        assert "calendars" in manifest
        assert isinstance(manifest["calendars"], list)

    def test_generate_manifest_structure(self, calendars_with_single_team, tmp_path):
        """Test that manifest has correct structure."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        with open(output_file) as f:
            manifest = json.load(f)

        assert len(manifest["calendars"]) == 1
        league = manifest["calendars"][0]

        assert "league" in league
        assert "slug" in league
        assert "teams" in league
        assert league["slug"] == "premier-league"
        assert len(league["teams"]) == 1

    def test_generate_manifest_team_structure(
        self, calendars_with_single_team, tmp_path
    ):
        """Test that team structure in manifest is correct."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        with open(output_file) as f:
            manifest = json.load(f)

        team = manifest["calendars"][0]["teams"][0]

        assert "name" in team
        assert "slug" in team
        assert "competitions" in team
        assert team["slug"] == "manchester-united"
        assert team["name"] == "Manchester United"

    def test_generate_manifest_competition_structure(
        self, calendars_with_single_team, tmp_path
    ):
        """Test that competition structure in manifest is correct."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        with open(output_file) as f:
            manifest = json.load(f)

        competition = manifest["calendars"][0]["teams"][0]["competitions"][0]

        assert "code" in competition
        assert "name" in competition
        assert "url" in competition
        assert competition["code"] == "PL"
        assert competition["name"] == "Premier League"

    def test_generate_manifest_multiple_competitions(
        self, calendars_with_multiple_competitions, tmp_path
    ):
        """Test manifest with multiple competitions for one team."""
        calendars_dir, _ = calendars_with_multiple_competitions
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        with open(output_file) as f:
            manifest = json.load(f)

        competitions = manifest["calendars"][0]["teams"][0]["competitions"]

        assert len(competitions) == 2
        codes = [comp["code"] for comp in competitions]
        assert "PL" in codes
        assert "FA" in codes

    def test_generate_manifest_multiple_teams(
        self, calendars_with_multiple_teams, tmp_path
    ):
        """Test manifest with multiple teams."""
        calendars_dir, _ = calendars_with_multiple_teams
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        with open(output_file) as f:
            manifest = json.load(f)

        teams = manifest["calendars"][0]["teams"]

        assert len(teams) == 2
        team_names = [team["name"] for team in teams]
        assert "Manchester United" in team_names
        assert "Liverpool" in team_names

    def test_generate_manifest_multiple_leagues(
        self, calendars_with_multiple_leagues, tmp_path
    ):
        """Test manifest with multiple leagues."""
        calendars_dir, _ = calendars_with_multiple_leagues
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        with open(output_file) as f:
            manifest = json.load(f)

        leagues = manifest["calendars"]

        assert len(leagues) == 2
        league_names = [league["league"] for league in leagues]
        assert "Premier League" in league_names
        assert "Championship" in league_names

    def test_generate_manifest_ignores_files_in_calendars_root(self, tmp_path):
        """Test that files in calendars root directory are ignored."""
        calendars_dir = tmp_path / "calendars"
        calendars_dir.mkdir()

        # Create a file in the root of calendars directory
        (calendars_dir / "README.md").write_text("# Calendars")

        # Create proper directory structure
        league_dir = calendars_dir / "premier-league"
        team_dir = league_dir / "manchester-united"
        team_dir.mkdir(parents=True)
        ics_file = team_dir / "manchester-united.pl.ics"
        ics_file.write_text("BEGIN:VCALENDAR\nEND:VCALENDAR")

        output_file = tmp_path / "manifest.json"
        generate_manifest(calendars_dir, output_file)

        with open(output_file) as f:
            manifest = json.load(f)

        assert len(manifest["calendars"]) == 1

    def test_generate_manifest_ignores_non_matching_ics_files(self, tmp_path):
        """Test that ICS files not matching pattern are ignored."""
        calendars_dir = tmp_path / "calendars"
        league_dir = calendars_dir / "premier-league"
        team_dir = league_dir / "manchester-united"
        team_dir.mkdir(parents=True)

        # Create files that don't match the pattern
        (team_dir / "other-file.ics").write_text("BEGIN:VCALENDAR\nEND:VCALENDAR")
        (team_dir / "manchester-united.pl.ics").write_text(
            "BEGIN:VCALENDAR\nEND:VCALENDAR"
        )

        output_file = tmp_path / "manifest.json"
        generate_manifest(calendars_dir, output_file)

        with open(output_file) as f:
            manifest = json.load(f)

        competitions = manifest["calendars"][0]["teams"][0]["competitions"]

        # Should only have one competition from the matching file
        assert len(competitions) == 1

    def test_generate_manifest_creates_output_directory(self, tmp_path):
        """Test that generate_manifest creates output directory if it doesn't exist."""
        calendars_dir = tmp_path / "calendars"
        output_file = tmp_path / "nonexistent" / "subdir" / "manifest.json"

        league_dir = calendars_dir / "premier-league"
        team_dir = league_dir / "manchester-united"
        team_dir.mkdir(parents=True)
        ics_file = team_dir / "manchester-united.pl.ics"
        ics_file.write_text("BEGIN:VCALENDAR\nEND:VCALENDAR")

        generate_manifest(calendars_dir, output_file)

        assert output_file.parent.exists()
        assert output_file.exists()

    def test_generate_manifest_empty_calendars_dir(self, tmp_path):
        """Test generate_manifest with empty calendars directory."""
        calendars_dir = tmp_path / "calendars"
        calendars_dir.mkdir()
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        assert output_file.exists()

        with open(output_file) as f:
            manifest = json.load(f)

        assert manifest["calendars"] == []

    def test_generate_manifest_nonexistent_calendars_dir(self, tmp_path):
        """Test generate_manifest with nonexistent calendars directory."""
        calendars_dir = tmp_path / "nonexistent"
        output_file = tmp_path / "manifest.json"

        with patch("utils.manifest.logger") as mock_logger:
            generate_manifest(calendars_dir, output_file)
            mock_logger.warning.assert_called_once()

    def test_generate_manifest_url_format(self, calendars_with_single_team, tmp_path):
        """Test that URLs in manifest are properly formatted."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        with open(output_file) as f:
            manifest = json.load(f)

        url = manifest["calendars"][0]["teams"][0]["competitions"][0]["url"]

        # URL should start with "calendars/" (relative to public directory)
        assert url.startswith("calendars/")
        assert url.endswith(".ics")
        # Should use forward slashes only
        assert "\\" not in url

    def test_generate_manifest_sorted_output(self, tmp_path):
        """Test that manifest output is sorted by league and team."""
        calendars_dir = tmp_path / "calendars"

        # Create leagues in non-alphabetical order
        for league_slug in ["championship", "premier-league"]:
            league_dir = calendars_dir / league_slug
            for team_slug in ["zebras", "arsenal"]:
                team_dir = league_dir / team_slug
                team_dir.mkdir(parents=True)
                ics_file = team_dir / f"{team_slug}.pl.ics"
                ics_file.write_text("BEGIN:VCALENDAR\nEND:VCALENDAR")

        output_file = tmp_path / "manifest.json"
        generate_manifest(calendars_dir, output_file)

        with open(output_file) as f:
            manifest = json.load(f)

        # Check league order
        league_slugs = [league["slug"] for league in manifest["calendars"]]
        assert league_slugs == sorted(league_slugs)

        # Check team order within each league
        for league in manifest["calendars"]:
            team_slugs = [team["slug"] for team in league["teams"]]
            assert team_slugs == sorted(team_slugs)

    def test_generate_manifest_preserves_directory_structure(self, tmp_path):
        """Test that manifest correctly reflects directory structure."""
        calendars_dir = tmp_path / "calendars"

        # Create specific directory structure
        league_dir = calendars_dir / "premier-league"
        team_dir = league_dir / "manchester-city"
        team_dir.mkdir(parents=True)
        ics_file = team_dir / "manchester-city.pl.ics"
        ics_file.write_text("BEGIN:VCALENDAR\nEND:VCALENDAR")

        output_file = tmp_path / "manifest.json"
        generate_manifest(calendars_dir, output_file)

        with open(output_file) as f:
            manifest = json.load(f)

        assert manifest["calendars"][0]["slug"] == "premier-league"
        assert manifest["calendars"][0]["league"] == "Premier League"
        assert manifest["calendars"][0]["teams"][0]["slug"] == "manchester-city"
        assert manifest["calendars"][0]["teams"][0]["name"] == "Manchester City"

    @patch("utils.manifest.logger")
    def test_generate_manifest_logs_info(
        self, mock_logger, calendars_with_single_team, tmp_path
    ):
        """Test that generate_manifest logs information."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        # Check that logger.info was called
        assert mock_logger.info.called

    @patch("utils.manifest.logger")
    def test_generate_manifest_logs_debug(
        self, mock_logger, calendars_with_single_team, tmp_path
    ):
        """Test that generate_manifest logs debug information."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        # Check that logger.debug was called
        assert mock_logger.debug.called

    def test_generate_manifest_empty_team_directory_ignored(self, tmp_path):
        """Test that empty team directories are ignored."""
        calendars_dir = tmp_path / "calendars"
        league_dir = calendars_dir / "premier-league"

        # Create one empty team directory
        empty_team_dir = league_dir / "empty-team"
        empty_team_dir.mkdir(parents=True)

        # Create one valid team directory
        valid_team_dir = league_dir / "valid-team"
        valid_team_dir.mkdir(parents=True)
        ics_file = valid_team_dir / "valid-team.pl.ics"
        ics_file.write_text("BEGIN:VCALENDAR\nEND:VCALENDAR")

        output_file = tmp_path / "manifest.json"
        generate_manifest(calendars_dir, output_file)

        with open(output_file) as f:
            manifest = json.load(f)

        # Should only have one team (the valid one)
        assert len(manifest["calendars"][0]["teams"]) == 1
        assert manifest["calendars"][0]["teams"][0]["slug"] == "valid-team"

    def test_generate_manifest_empty_league_directory_ignored(self, tmp_path):
        """Test that empty league directories are ignored."""
        calendars_dir = tmp_path / "calendars"

        # Create one empty league directory
        empty_league_dir = calendars_dir / "empty-league"
        empty_league_dir.mkdir(parents=True)

        # Create one valid league directory
        valid_league_dir = calendars_dir / "premier-league"
        team_dir = valid_league_dir / "valid-team"
        team_dir.mkdir(parents=True)
        ics_file = team_dir / "valid-team.pl.ics"
        ics_file.write_text("BEGIN:VCALENDAR\nEND:VCALENDAR")

        output_file = tmp_path / "manifest.json"
        generate_manifest(calendars_dir, output_file)

        with open(output_file) as f:
            manifest = json.load(f)

        # Should only have one league
        assert len(manifest["calendars"]) == 1
        assert manifest["calendars"][0]["slug"] == "premier-league"


# Matches the calendars_with_single_team fixture, whose directory slug is
# "manchester-united" — the cache key is the full name, keyed by short name
TEAM_CACHE = {
    "Premier League": {
        "Manchester United FC": {
            "id": 66,
            "short_name": "Manchester United",
            "venue": "Old Trafford",
            "club_colors": "Red / White",
            "crest": "https://crests.football-data.org/66.png",
        }
    }
}


def _first_team(output_file):
    """Read the first team out of a generated manifest.

    Args:
        output_file: Path to the generated manifest.

    Returns:
        The first team entry of the first league.
    """
    with open(output_file) as f:
        return json.load(f)["calendars"][0]["teams"][0]


class TestGenerateManifestTeamMetadata:
    """Tests for colour, crest and name enrichment from the team cache."""

    def test_no_cache_omits_colour_and_crest(
        self, calendars_with_single_team, tmp_path
    ):
        """Test the manifest is unchanged when no cache is supplied."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)
        team = _first_team(output_file)

        assert team["name"] == "Manchester United"
        assert "color" not in team
        assert "text_on_color" not in team
        assert "crest" not in team

    def test_cache_adds_colour_crest_and_real_name(
        self, calendars_with_single_team, tmp_path
    ):
        """Test cached metadata is emitted alongside the real team name."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file, team_cache=TEAM_CACHE)
        team = _first_team(output_file)

        assert team["name"] == "Manchester United FC"
        assert team["slug"] == "manchester-united"
        assert team["color"] == "#D50000"
        assert team["text_on_color"] == "#ffffff"
        assert team["crest"] == "https://crests.football-data.org/66.png"

    def test_override_beats_derived_colour(self, calendars_with_single_team, tmp_path):
        """Test a curated colour wins over the one derived from club colours."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(
            calendars_dir,
            output_file,
            team_cache=TEAM_CACHE,
            color_overrides={"Manchester United FC": "#CF271B"},
        )
        team = _first_team(output_file)

        assert team["color"] == "#CF271B"
        assert team["text_on_color"] == "#ffffff"

    def test_override_keyed_on_full_name_not_slug(
        self, calendars_with_single_team, tmp_path
    ):
        """Test overrides that don't match a cached name are ignored."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(
            calendars_dir,
            output_file,
            team_cache=TEAM_CACHE,
            color_overrides={"manchester-united": "#CF271B"},
        )
        team = _first_team(output_file)

        assert team["color"] == "#D50000"

    def test_team_missing_from_cache_falls_back(
        self, calendars_with_single_team, tmp_path
    ):
        """Test an uncached team keeps the un-slugged name and gains no colour."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(
            calendars_dir,
            output_file,
            team_cache={"Premier League": {"Arsenal FC": {"short_name": "Arsenal"}}},
        )
        team = _first_team(output_file)

        assert team["name"] == "Manchester United"
        assert "color" not in team
        assert "crest" not in team

    def test_null_colours_and_crest_are_omitted(
        self, calendars_with_single_team, tmp_path
    ):
        """Test the API's nulls never reach the manifest."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(
            calendars_dir,
            output_file,
            team_cache={
                "Premier League": {
                    "Manchester United FC": {
                        "short_name": "Manchester United",
                        "club_colors": None,
                        "crest": None,
                    }
                }
            },
        )
        team = _first_team(output_file)

        assert team["name"] == "Manchester United FC"
        assert "color" not in team
        assert "text_on_color" not in team
        assert "crest" not in team

    def test_team_cached_without_short_name(self, calendars_with_single_team, tmp_path):
        """Test teams added by _add_to_cache still match on their full name."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(
            calendars_dir,
            output_file,
            team_cache={
                "Premier League": {
                    "Manchester United": {"crest": "https://example.com/66.png"}
                }
            },
        )
        team = _first_team(output_file)

        assert team["crest"] == "https://example.com/66.png"
        assert "color" not in team

    def test_unmappable_club_colours_omit_colour(
        self, calendars_with_single_team, tmp_path
    ):
        """Test colours the word map doesn't know leave the CSS default in place."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(
            calendars_dir,
            output_file,
            team_cache={
                "Premier League": {
                    "Manchester United FC": {
                        "short_name": "Manchester United",
                        "club_colors": "Turquoise / Beige",
                    }
                }
            },
        )
        team = _first_team(output_file)

        assert "color" not in team

    def test_competitions_key_is_last(self, calendars_with_single_team, tmp_path):
        """Test the competitions list stays at the end of each team entry."""
        calendars_dir, _ = calendars_with_single_team
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file, team_cache=TEAM_CACHE)
        team = _first_team(output_file)

        assert list(team)[-1] == "competitions"


class TestLoadColorOverrides:
    """Tests for load_color_overrides function."""

    def test_flattens_leagues(self, tmp_path):
        """Test per-league grouping is flattened to a single mapping."""
        path = tmp_path / "team_colors.yaml"
        path.write_text(
            'Premier League:\n  "Arsenal FC": "#D70106"\n'
            'Championship:\n  "Leeds United FC": "#1D428A"\n'
        )

        assert load_color_overrides(path) == {
            "Arsenal FC": "#D70106",
            "Leeds United FC": "#1D428A",
        }

    def test_missing_file_returns_empty(self, tmp_path):
        """Test a missing overrides file is not fatal."""
        assert load_color_overrides(tmp_path / "nope.yaml") == {}

    def test_malformed_yaml_returns_empty(self, tmp_path):
        """Test unparseable YAML is not fatal."""
        path = tmp_path / "team_colors.yaml"
        path.write_text("Premier League:\n  - [unclosed\n")

        assert load_color_overrides(path) == {}

    def test_invalid_colours_are_skipped(self, tmp_path):
        """Test only well-formed #RRGGBB values survive."""
        path = tmp_path / "team_colors.yaml"
        path.write_text(
            "Premier League:\n"
            '  "Good FC": "#D70106"\n'
            '  "Short FC": "#FFF"\n'
            '  "No Hash FC": "D70106"\n'
            '  "Named FC": "red"\n'
            '  "Null FC": null\n'
        )

        assert load_color_overrides(path) == {"Good FC": "#D70106"}

    def test_non_mapping_league_is_skipped(self, tmp_path):
        """Test a league entry that isn't a mapping doesn't abort the load."""
        path = tmp_path / "team_colors.yaml"
        path.write_text(
            "Premier League:\n  - Arsenal FC\n"
            'Championship:\n  "Leeds United FC": "#1D428A"\n'
        )

        assert load_color_overrides(path) == {"Leeds United FC": "#1D428A"}

    def test_low_contrast_colour_is_kept_but_warned(self, tmp_path, caplog):
        """Test a hard-to-read curated colour is honoured, with a warning."""
        path = tmp_path / "team_colors.yaml"
        path.write_text('Premier League:\n  "Pale FC": "#EEEEEE"\n')

        with caplog.at_level(logging.WARNING):
            assert load_color_overrides(path) == {"Pale FC": "#EEEEEE"}

        assert "contrast" in caplog.text


class TestNextFixture:
    """Tests for the next_fixture field of a manifest team entry."""

    def test_earliest_upcoming_kickoff_is_used(
        self, calendars_with_single_team, tmp_path
    ):
        """Test the soonest future match wins, not the first one written."""
        calendars_dir, team_dir = calendars_with_single_team
        # ICS has second precision, so drop microseconds before comparing
        now = datetime.now(timezone.utc).replace(microsecond=0)
        soonest = now + timedelta(days=3)

        (team_dir / "manchester-united.pl.ics").write_text(
            _ics(
                (now + timedelta(days=10), None),
                (soonest, None),
                (now + timedelta(days=20), None),
            )
        )
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        assert (
            _team_from(output_file)["next_fixture"] == soonest.astimezone().isoformat()
        )

    def test_past_fixtures_are_ignored(self, calendars_with_single_team, tmp_path):
        """Test a match already played is not reported as the next one."""
        calendars_dir, team_dir = calendars_with_single_team
        # ICS has second precision, so drop microseconds before comparing
        now = datetime.now(timezone.utc).replace(microsecond=0)
        upcoming = now + timedelta(days=5)

        (team_dir / "manchester-united.pl.ics").write_text(
            _ics((now - timedelta(days=2), None), (upcoming, None))
        )
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        assert (
            _team_from(output_file)["next_fixture"] == upcoming.astimezone().isoformat()
        )

    def test_cancelled_fixtures_are_skipped(self, calendars_with_single_team, tmp_path):
        """Test a called-off match stays in the feed but isn't the next fixture."""
        calendars_dir, team_dir = calendars_with_single_team
        # ICS has second precision, so drop microseconds before comparing
        now = datetime.now(timezone.utc).replace(microsecond=0)
        playable = now + timedelta(days=8)

        (team_dir / "manchester-united.pl.ics").write_text(
            _ics((now + timedelta(days=2), "CANCELLED"), (playable, None))
        )
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        assert (
            _team_from(output_file)["next_fixture"] == playable.astimezone().isoformat()
        )

    def test_omitted_when_nothing_upcoming(self, calendars_with_single_team, tmp_path):
        """Test the key is absent off-season rather than emitted as null."""
        calendars_dir, team_dir = calendars_with_single_team
        # ICS has second precision, so drop microseconds before comparing
        now = datetime.now(timezone.utc).replace(microsecond=0)

        (team_dir / "manchester-united.pl.ics").write_text(
            _ics((now - timedelta(days=30), None))
        )
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        assert "next_fixture" not in _team_from(output_file)

    def test_earliest_across_competitions(
        self, calendars_with_multiple_competitions, tmp_path
    ):
        """Test the next fixture spans all of a team's calendars."""
        calendars_dir, team_dir = calendars_with_multiple_competitions
        # ICS has second precision, so drop microseconds before comparing
        now = datetime.now(timezone.utc).replace(microsecond=0)
        cup_tie = now + timedelta(days=4)

        (team_dir / "manchester-united.pl.ics").write_text(
            _ics((now + timedelta(days=9), None))
        )
        (team_dir / "manchester-united.fa.ics").write_text(_ics((cup_tie, None)))
        output_file = tmp_path / "manifest.json"

        generate_manifest(calendars_dir, output_file)

        assert (
            _team_from(output_file)["next_fixture"] == cup_tie.astimezone().isoformat()
        )

    def test_unreadable_calendar_is_not_fatal(
        self, calendars_with_multiple_competitions, tmp_path, caplog
    ):
        """Test a corrupt file costs its own date, not the whole manifest."""
        calendars_dir, team_dir = calendars_with_multiple_competitions
        # ICS has second precision, so drop microseconds before comparing
        now = datetime.now(timezone.utc).replace(microsecond=0)
        readable = now + timedelta(days=6)

        (team_dir / "manchester-united.pl.ics").write_text("not a calendar at all")
        (team_dir / "manchester-united.fa.ics").write_text(_ics((readable, None)))
        output_file = tmp_path / "manifest.json"

        with caplog.at_level(logging.WARNING):
            generate_manifest(calendars_dir, output_file)

        team = _team_from(output_file)

        assert team["next_fixture"] == readable.astimezone().isoformat()
        assert len(team["competitions"]) == 2
