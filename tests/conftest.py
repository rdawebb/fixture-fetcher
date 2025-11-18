"""Pytest configuration and shared fixtures."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pytest

from src.models import Fixture


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
