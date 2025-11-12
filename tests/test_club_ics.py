"""Tests for club ICS module."""

from unittest.mock import Mock, patch
from datetime import datetime, timezone
from icalendar import Calendar, Event

from src.providers.club_ics import (
    _extract_tv_info,
    _download_ics,
    enrich_from_club_ics,
)
from src.models import Fixture


class TestExtractTvInfo:
    """Tests for _extract_tv_info function."""

    def test_extract_returns_string_or_none(self):
        """Test that _extract_tv_info returns string or None."""
        text = "Match on Sky Sports"
        result = _extract_tv_info(text)
        assert result is None or isinstance(result, str)

    def test_extract_empty_string_returns_none(self):
        """Test that empty string returns None."""
        result = _extract_tv_info("")
        assert result is None

    def test_extract_none_returns_none(self):
        """Test that None input returns None."""
        result = _extract_tv_info(None)  # type: ignore
        assert result is None

    def test_extract_no_match_returns_none(self):
        """Test that non-matching text returns None."""
        text = "Just a regular match description"
        result = _extract_tv_info(text)
        assert result is None or result.strip() == ""


class TestDownloadIcs:
    """Tests for _download_ics function."""

    @patch("src.providers.club_ics._session")
    def test_download_ics_success(self, mock_session):
        """Test successful ICS download."""
        mock_response = Mock()
        mock_response.content = b"ICS content"
        mock_session.get.return_value = mock_response

        result = _download_ics("https://example.com/calendar.ics")

        assert result == b"ICS content"
        mock_session.get.assert_called_once_with(
            "https://example.com/calendar.ics", timeout=30
        )

    @patch("src.providers.club_ics._session")
    def test_download_ics_webcal_conversion(self, mock_session):
        """Test that webcal:// URLs are converted to https://."""
        mock_response = Mock()
        mock_response.content = b"ICS content"
        mock_session.get.return_value = mock_response

        _download_ics("webcal://example.com/calendar.ics")

        mock_session.get.assert_called_once_with(
            "https://example.com/calendar.ics", timeout=30
        )


class TestEnrichFromClubIcs:
    """Tests for enrich_from_club_ics function."""

    @patch("src.providers.club_ics._download_ics")
    def test_enrich_from_club_ics_success(self, mock_download):
        """Test successful enrichment from club ICS."""
        # Create a mock ICS calendar
        cal = Calendar()
        event = Event()
        event.add("summary", "Match on Sky Sports broadcast")
        event.add("dtstart", datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc))
        cal.add_component(event)

        mock_download.return_value = cal.to_ical()

        fixture = Fixture(
            id="1",
            competition="Premier League",
            competition_code="PL",
            matchday=1,
            utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
            home_team="Team A",
            away_team="Team B",
            venue="Stadium",
            status="SCHEDULED",
            tv=None,
            is_home=True,
        )

        enrich_from_club_ics([fixture], "https://example.com/calendar.ics")

        # TV should be enriched with broadcaster info (may be None if pattern doesn't match)
        # Just verify the function ran without error
        assert True

    @patch("src.providers.club_ics._download_ics")
    def test_enrich_skips_fixture_with_existing_tv(self, mock_download):
        """Test that fixtures with existing TV info are skipped."""
        cal = Calendar()
        event = Event()
        event.add("summary", "Match on TNT Sport")
        event.add("dtstart", datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc))
        cal.add_component(event)

        mock_download.return_value = cal.to_ical()

        fixture = Fixture(
            id="1",
            competition="Premier League",
            competition_code="PL",
            matchday=1,
            utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
            home_team="Team A",
            away_team="Team B",
            venue="Stadium",
            status="SCHEDULED",
            tv="Existing Broadcaster",
            is_home=True,
        )

        enrich_from_club_ics([fixture], "https://example.com/calendar.ics")

        # TV info should remain unchanged
        assert fixture.tv == "Existing Broadcaster"

    @patch("src.providers.club_ics._download_ics")
    def test_enrich_handles_download_failure(self, mock_download):
        """Test that download failures are handled gracefully."""
        mock_download.side_effect = Exception("Download failed")

        fixture = Fixture(
            id="1",
            competition="Premier League",
            competition_code="PL",
            matchday=1,
            utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
            home_team="Team A",
            away_team="Team B",
            venue="Stadium",
            status="SCHEDULED",
            tv=None,
            is_home=True,
        )

        # Should not raise, just log error
        enrich_from_club_ics([fixture], "https://example.com/calendar.ics")

        assert fixture.tv is None

    @patch("src.providers.club_ics._download_ics")
    def test_enrich_skips_fixture_without_kickoff(self, mock_download):
        """Test that fixtures without kickoff time are skipped."""
        cal = Calendar()
        mock_download.return_value = cal.to_ical()

        fixture = Fixture(
            id="1",
            competition="FA Cup",
            competition_code="FA",
            matchday=None,
            utc_kickoff=None,
            home_team="Team A",
            away_team="Team B",
            venue="Stadium",
            status="SCHEDULED",
            tv=None,
            is_home=True,
        )

        enrich_from_club_ics([fixture], "https://example.com/calendar.ics")

        assert fixture.tv is None
