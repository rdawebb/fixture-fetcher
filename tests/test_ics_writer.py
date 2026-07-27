"""Tests for the ICS writer module."""

from datetime import datetime, timezone

from icalendar import Calendar

from logic.calendar.ics_writer import ICSWriter
from logic.fixtures.models import Fixture


class TestICSWriter:
    """Tests for the ICSWriter class."""

    def test_ics_writer_initialization(self, sample_fixtures):
        """Test ICSWriter initialization."""
        writer = ICSWriter(sample_fixtures)
        assert writer.fixtures == sample_fixtures

    def test_write_ics_file(self, sample_fixtures, tmp_path):
        """Test writing fixtures to ICS file."""
        output_path = tmp_path / "test.ics"
        writer = ICSWriter(sample_fixtures)

        result_path = writer.write(output_path)

        assert result_path == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_ics_file_content(self, sample_fixture, tmp_path):
        """Test that ICS file contains expected content."""
        output_path = tmp_path / "test.ics"
        writer = ICSWriter([sample_fixture])
        writer.write(output_path)

        content = output_path.read_text()

        assert "BEGIN:VCALENDAR" in content
        assert "END:VCALENDAR" in content
        assert "Manchester United vs Liverpool" in content
        assert "PL" in content
        assert "Old Trafford" in content

    def test_ics_file_parsing(self, sample_fixtures, tmp_path):
        """Test that written ICS file can be parsed."""
        output_path = tmp_path / "test.ics"
        writer = ICSWriter(sample_fixtures)
        writer.write(output_path)

        # Parse the written file
        with open(output_path, "rb") as f:
            cal = Calendar.from_ical(f.read())

        events = [c for c in cal.walk() if c.name == "VEVENT"]
        dated = [f for f in sample_fixtures if f.utc_kickoff is not None]
        assert len(events) == len(dated)

    def test_fixture_without_kickoff_is_skipped(self, tmp_path):
        """Test that a fixture with no kickoff date produces no event.

        A VEVENT without DTSTART is invalid per RFC 5545, and Fixture carries no
        other date to fall back on, so such fixtures are omitted entirely.
        """
        fixture = Fixture(
            id="999",
            competition="FA Cup",
            competition_code="FA",
            matchday=None,
            utc_kickoff=None,
            home_team="Team A",
            away_team="Team B",
            venue=None,
            status="SCHEDULED",
            tv=None,
            is_home=True,
        )

        output_path = tmp_path / "test.ics"
        writer = ICSWriter([fixture])
        writer.write(output_path)

        with open(output_path, "rb") as f:
            cal = Calendar.from_ical(f.read())

        assert [c for c in cal.walk() if c.name == "VEVENT"] == []
        assert "Team A" not in output_path.read_text()

    def test_dateless_fixture_does_not_suppress_others(self, sample_fixture, tmp_path):
        """Test that a dateless fixture doesn't stop valid ones being written."""
        dateless = Fixture(
            id="999",
            competition="FA Cup",
            competition_code="FA",
            matchday=None,
            utc_kickoff=None,
            home_team="Team A",
            away_team="Team B",
            venue=None,
            status="SCHEDULED",
            tv=None,
            is_home=True,
        )

        output_path = tmp_path / "test.ics"
        ICSWriter([dateless, sample_fixture]).write(output_path)

        with open(output_path, "rb") as f:
            cal = Calendar.from_ical(f.read())

        events = [c for c in cal.walk() if c.name == "VEVENT"]
        assert len(events) == 1
        assert str(events[0]["UID"]) == "12345@fixture-fetcher"

    def test_events_have_required_rfc5545_properties(self, sample_fixtures, tmp_path):
        """Test that every written VEVENT carries the properties RFC 5545 requires."""
        output_path = tmp_path / "test.ics"
        ICSWriter(sample_fixtures).write(output_path)

        with open(output_path, "rb") as f:
            cal = Calendar.from_ical(f.read())

        events = [c for c in cal.walk() if c.name == "VEVENT"]
        assert events

        for event in events:
            # UID and DTSTAMP are mandatory for every VEVENT; DTSTART is
            # mandatory for a calendar without a METHOD property
            assert event.get("UID"), "VEVENT missing UID"
            assert event.get("DTSTAMP"), "VEVENT missing DTSTAMP"
            assert event.get("DTSTART"), "VEVENT missing DTSTART"

    def test_dtstamp_is_utc_and_current(self, sample_fixture, tmp_path):
        """Test that DTSTAMP is written as an aware UTC timestamp."""
        # ICS serialises to whole seconds, so compare against a truncated bound
        before = datetime.now(timezone.utc).replace(microsecond=0)

        output_path = tmp_path / "test.ics"
        ICSWriter([sample_fixture]).write(output_path)

        with open(output_path, "rb") as f:
            cal = Calendar.from_ical(f.read())

        event = next(c for c in cal.walk() if c.name == "VEVENT")
        dtstamp = event["DTSTAMP"].dt

        assert dtstamp.tzinfo is not None
        assert before <= dtstamp <= datetime.now(timezone.utc)

    def test_write_creates_parent_directories(self, tmp_path):
        """Test that write creates parent directories if they don't exist."""
        output_path = tmp_path / "nested" / "dir" / "test.ics"
        writer = ICSWriter([])

        writer.write(output_path)

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_empty_fixtures_list(self, tmp_path):
        """Test writing empty fixtures list."""
        output_path = tmp_path / "test.ics"
        writer = ICSWriter([])

        result_path = writer.write(output_path)

        assert result_path == output_path
        assert output_path.exists()

    def test_uid_generation(self, sample_fixture):
        """Test UID generation for events."""
        from logic.calendar.formatter import EventFormatter

        formatter = EventFormatter()
        uid = formatter._uid(sample_fixture)

        assert uid == "12345@fixture-fetcher"
        assert "@" in uid
