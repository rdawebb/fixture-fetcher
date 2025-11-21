"""Tests for the models module."""

from datetime import datetime, timezone

from src.logic.fixtures.models import Fixture


class TestFixture:
    """Tests for the Fixture data class."""

    def test_fixture_creation(self):
        """Test creating a Fixture instance."""
        fixture = Fixture(
            id="123",
            competition="Premier League",
            competition_code="PL",
            matchday=5,
            utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
            home_team="Manchester United",
            away_team="Liverpool",
            venue="Old Trafford",
            status="SCHEDULED",
            tv="Sky Sports",
            is_home=True,
        )

        assert fixture.id == "123"
        assert fixture.competition == "Premier League"
        assert fixture.competition_code == "PL"
        assert fixture.matchday == 5
        assert fixture.home_team == "Manchester United"
        assert fixture.away_team == "Liverpool"
        assert fixture.venue == "Old Trafford"
        assert fixture.status == "SCHEDULED"
        assert fixture.tv == "Sky Sports"
        assert fixture.is_home is True

    def test_fixture_str_home(self, sample_fixture):
        """Test string representation for home fixture."""
        expected = "Manchester United vs Liverpool (Premier League)"
        assert str(sample_fixture) == expected

    def test_fixture_str_away(self):
        """Test string representation for away fixture."""
        fixture = Fixture(
            id="123",
            competition="Champions League",
            competition_code="CL",
            matchday=1,
            utc_kickoff=datetime(2025, 11, 20, 20, 0, 0, tzinfo=timezone.utc),
            home_team="Barcelona",
            away_team="Manchester United",
            venue="Camp Nou",
            status="SCHEDULED",
            tv=None,
            is_home=False,
        )
        expected = "Barcelona @ Manchester United (Champions League)"
        assert str(fixture) == expected

    def test_fixture_with_none_values(self):
        """Test fixture with optional None values."""
        fixture = Fixture(
            id="456",
            competition="FA Cup",
            competition_code="FA",
            matchday=None,
            utc_kickoff=None,
            home_team="West Ham",
            away_team="Chelsea",
            venue=None,
            status="POSTPONED",
            tv=None,
            is_home=True,
        )

        assert fixture.matchday is None
        assert fixture.utc_kickoff is None
        assert fixture.venue is None
        assert fixture.tv is None
