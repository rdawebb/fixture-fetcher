"""Tests for the ICS writer module."""

from icalendar import Calendar

from src.logic.calendar.ics_writer import ICSWriter
from src.logic.fixtures.models import Fixture


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
        assert len(events) == len(sample_fixtures)

    def test_fixture_without_kickoff(self, tmp_path):
        """Test handling fixture without kickoff time."""
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

        content = output_path.read_text()
        assert "Team A vs Team B (TBC)" in content
        assert "Kickoff TBC" in content

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
        from src.logic.calendar.formatter import EventFormatter

        formatter = EventFormatter()
        uid = formatter._uid(sample_fixture)

        assert uid == "12345@fixture-fetcher"
        assert "@" in uid
