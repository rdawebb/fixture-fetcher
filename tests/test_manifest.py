"""Tests for the manifest module."""

import json
from unittest.mock import patch

import pytest

from utils.manifest import (
    generate_manifest,
    _unslug,
    _get_competition_name,
)


class TestUnslug:
    """Tests for _unslug function."""

    @pytest.mark.parametrize(
        "input_slug,uppercase,expected",
        [
            ("premier", False, "Premier"),
            ("premier-league", False, "Premier League"),
            ("fa-cup-championship", False, "Fa Cup Championship"),
            ("premier-league", False, "Premier League"),
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
