"""Pytest configuration and shared fixtures."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List
from unittest.mock import Mock, patch

import pytest
import yaml

from logic.fixtures.models import Fixture
from backend.api.football_data import FDClient


@pytest.fixture
def sample_fixture() -> Fixture:
    """Create a sample fixture for testing."""
    return Fixture(
        id="12345",
        competition="Premier League",
        competition_code="PL",
        matchday=10,
        utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
        home_team="Manchester United",
        away_team="Liverpool",
        venue="Old Trafford",
        status="SCHEDULED",
        tv="Sky Sports",
        is_home=True,
    )


@pytest.fixture
def sample_fixtures() -> List[Fixture]:
    """Create a list of sample fixtures for testing."""
    return [
        Fixture(
            id="1",
            competition="Premier League",
            competition_code="PL",
            matchday=1,
            utc_kickoff=datetime(2025, 11, 10, 15, 0, 0, tzinfo=timezone.utc),
            home_team="Manchester United",
            away_team="Liverpool",
            venue="Old Trafford",
            status="SCHEDULED",
            tv="Sky Sports",
            is_home=True,
        ),
        Fixture(
            id="2",
            competition="Champions League",
            competition_code="CL",
            matchday=2,
            utc_kickoff=datetime(2025, 11, 12, 20, 0, 0, tzinfo=timezone.utc),
            home_team="Arsenal",
            away_team="Manchester United",
            venue="Emirates Stadium",
            status="SCHEDULED",
            tv=None,
            is_home=False,
        ),
        Fixture(
            id="3",
            competition="Premier League",
            competition_code="PL",
            matchday=3,
            utc_kickoff=datetime(2025, 11, 15, 17, 30, 0, tzinfo=timezone.utc),
            home_team="Chelsea",
            away_team="Manchester United",
            venue="Stamford Bridge",
            status="FINISHED",
            tv="TNT Sport",
            is_home=False,
        ),
        Fixture(
            id="4",
            competition="FA Cup",
            competition_code="FA",
            matchday=None,
            utc_kickoff=None,
            home_team="Manchester United",
            away_team="West Ham",
            venue="Old Trafford",
            status="TIMED",
            tv=None,
            is_home=True,
        ),
    ]


@pytest.fixture
def temp_yaml_file(tmp_path: Path) -> Path:
    """Create a temporary YAML file for testing."""
    yaml_file = tmp_path / "test.yaml"
    return yaml_file


@pytest.fixture
def mock_ics_url() -> str:
    """Return a mock ICS URL for testing."""
    return "webcal://example.com/calendar.ics"


# Football Data API Test Fixtures


@pytest.fixture
def mock_api_response():
    """Factory for creating mock API responses."""

    def _create_response(status_code=200, json_data=None, side_effect=None):
        response = Mock()
        response.status_code = status_code
        if json_data is not None:
            response.json.return_value = json_data
        if side_effect is not None:
            response.json.side_effect = side_effect
        return response

    return _create_response


@pytest.fixture
def sample_match_data():
    """Sample match data for API responses."""
    return {
        "id": "1",
        "status": "SCHEDULED",
        "utcDate": "2025-11-15T15:00:00Z",
        "homeTeam": {
            "name": "Manchester United",
            "shortName": "Man United",
            "id": 66,
        },
        "awayTeam": {
            "name": "Liverpool",
            "shortName": "Liverpool",
            "id": 64,
        },
        "venue": "Old Trafford",
        "competition": {"code": "PL", "name": "Premier League"},
        "matchday": 10,
    }


@pytest.fixture
def sample_team_data():
    """Sample team data for API responses."""
    return {
        "name": "Manchester United",
        "shortName": "Man Utd",
        "id": 66,
    }


@pytest.fixture
def mock_cache_path(tmp_path):
    """Fixture that patches CACHE_PATH and returns the path."""
    cache_file = tmp_path / "teams.yaml"
    with patch("backend.api.football_data.CACHE_PATH", cache_file):
        yield cache_file


@pytest.fixture
def fdclient_with_cache(mock_cache_path):
    """Fixture that returns an FDClient with mocked cache path."""
    with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
        return FDClient()


@pytest.fixture
def cache_with_teams(tmp_path):
    """Create a cache file with sample teams."""
    cache_file = tmp_path / "teams.yaml"
    cache_data = {
        "Premier League": {
            "Manchester United": {"id": 66, "short_name": "MUN"},
            "Liverpool": {"id": 64, "short_name": "LIV"},
        }
    }
    cache_file.write_text(yaml.safe_dump(cache_data))

    with patch("backend.api.football_data.CACHE_PATH", cache_file):
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            yield FDClient()


# Snapshot test fixtures


@pytest.fixture
def fixture_with_all_fields():
    """Fixture with all fields populated."""
    return Fixture(
        id="1",
        competition="Premier League",
        competition_code="PL",
        matchday=1,
        utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
        home_team="Team A",
        away_team="Team B",
        venue="Stadium A",
        status="SCHEDULED",
        tv="Sky Sports",
        is_home=True,
    )


@pytest.fixture
def fixture_without_optional_fields():
    """Fixture without optional fields (None values)."""
    return Fixture(
        id="2",
        competition="FA Cup",
        competition_code="FA",
        matchday=None,
        utc_kickoff=None,
        home_team="Team C",
        away_team="Team D",
        venue=None,
        status="SCHEDULED",
        tv=None,
        is_home=False,
    )


@pytest.fixture
def fixture_with_different_status():
    """Fixture with FINISHED status."""
    return Fixture(
        id="1",
        competition="Premier League",
        competition_code="PL",
        matchday=1,
        utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
        home_team="Team A",
        away_team="Team B",
        venue="Stadium A",
        status="FINISHED",
        tv="Sky Sports",
        is_home=True,
    )


@pytest.fixture
def fixture_with_different_time():
    """Fixture with different kickoff time."""
    return Fixture(
        id="1",
        competition="Premier League",
        competition_code="PL",
        matchday=1,
        utc_kickoff=datetime(2025, 11, 15, 16, 0, 0, tzinfo=timezone.utc),
        home_team="Team A",
        away_team="Team B",
        venue="Stadium A",
        status="SCHEDULED",
        tv="Sky Sports",
        is_home=True,
    )


@pytest.fixture
def fixture_with_different_venue():
    """Fixture with different venue."""
    return Fixture(
        id="1",
        competition="Premier League",
        competition_code="PL",
        matchday=1,
        utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
        home_team="Team A",
        away_team="Team B",
        venue="Stadium B",
        status="SCHEDULED",
        tv="Sky Sports",
        is_home=True,
    )


@pytest.fixture
def snapshot_from_fixture(fixture_with_all_fields, tmp_path):
    """Create and load a snapshot from a fixture."""
    from backend.storage.snapshot import save_snapshot, load_snapshot

    snapshot_path = tmp_path / "snapshot.json"
    save_snapshot([fixture_with_all_fields], snapshot_path)
    return load_snapshot(snapshot_path)


# Manifest test fixtures


@pytest.fixture
def calendars_with_single_team(tmp_path):
    """Create a calendars directory with a single team and competition."""
    calendars_dir = tmp_path / "calendars"
    league_dir = calendars_dir / "premier-league"
    team_dir = league_dir / "manchester-united"
    team_dir.mkdir(parents=True)

    ics_file = team_dir / "manchester-united.pl.ics"
    ics_file.write_text("BEGIN:VCALENDAR\nEND:VCALENDAR")

    return calendars_dir, team_dir


@pytest.fixture
def calendars_with_multiple_teams(tmp_path):
    """Create a calendars directory with multiple teams in one league."""
    calendars_dir = tmp_path / "calendars"
    league_dir = calendars_dir / "premier-league"

    teams = []
    for team_slug in ["manchester-united", "liverpool"]:
        team_dir = league_dir / team_slug
        team_dir.mkdir(parents=True)
        ics_file = team_dir / f"{team_slug}.pl.ics"
        ics_file.write_text("BEGIN:VCALENDAR\nEND:VCALENDAR")
        teams.append(team_dir)

    return calendars_dir, teams


@pytest.fixture
def calendars_with_multiple_competitions(tmp_path):
    """Create a calendars directory with a team having multiple competitions."""
    calendars_dir = tmp_path / "calendars"
    league_dir = calendars_dir / "premier-league"
    team_dir = league_dir / "manchester-united"
    team_dir.mkdir(parents=True)

    for comp_code in ["pl", "fa"]:
        ics_file = team_dir / f"manchester-united.{comp_code}.ics"
        ics_file.write_text("BEGIN:VCALENDAR\nEND:VCALENDAR")

    return calendars_dir, team_dir


@pytest.fixture
def calendars_with_multiple_leagues(tmp_path):
    """Create a calendars directory with multiple leagues."""
    calendars_dir = tmp_path / "calendars"
    leagues = []

    for league_slug in ["premier-league", "championship"]:
        league_dir = calendars_dir / league_slug
        team_dir = league_dir / "team-one"
        team_dir.mkdir(parents=True)
        ics_file = team_dir / "team-one.pl.ics"
        ics_file.write_text("BEGIN:VCALENDAR\nEND:VCALENDAR")
        leagues.append(league_dir)

    return calendars_dir, leagues
