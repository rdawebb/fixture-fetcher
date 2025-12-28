"""Tests for the calendar comparison module."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from icalendar import Calendar, Event

from src.logic.calendar.compare import CalendarComparison
from src.utils import ICSReadError


class TestCalendarComparison:
    """Tests for the CalendarComparison class."""

    @pytest.fixture
    def comparison(self):
        """Create a CalendarComparison instance."""
        return CalendarComparison()

    def _create_ics_file(self, path: Path, events: list[dict]) -> None:
        """Helper to create an ICS file with given events.

        Args:
            path: Path to write the ICS file to.
            events: List of event dicts with keys:
                - uid: Unique identifier
                - summary: Event summary/title
                - dtstart: Datetime object (or 'past' for past event, 'future' for future)
                - description: Event description
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        cal = Calendar()
        cal.add("prodid", "-//Test//Test//EN")
        cal.add("version", "2.0")

        now = datetime.now(timezone.utc)

        for event_data in events:
            event = Event()
            event.add("uid", event_data.get("uid", "test-uid"))
            event.add("summary", event_data.get("summary", "Test Event"))
            event.add("description", event_data.get("description", ""))

            # Handle different date formats
            dtstart = event_data.get("dtstart")
            if dtstart == "past":
                dtstart = now - timedelta(hours=1)
            elif dtstart == "future":
                dtstart = now + timedelta(hours=1)
            elif dtstart is None:
                dtstart = now + timedelta(hours=1)

            event.add("dtstart", dtstart)
            event.add("dtend", dtstart + timedelta(hours=2))

            cal.add_component(event)

        with open(path, "wb") as f:
            f.write(cal.to_ical())

    def test_initialization(self, comparison):
        """Test CalendarComparison initialization."""
        assert comparison is not None
        assert hasattr(comparison, "get_upcoming_events")
        assert hasattr(comparison, "compare_calendars")

    def test_get_upcoming_events_success(self, comparison, tmp_path):
        """Test getting upcoming events from a valid ICS file."""
        ics_file = tmp_path / "test.ics"
        self._create_ics_file(
            ics_file,
            [
                {
                    "uid": "event1",
                    "summary": "Future Event",
                    "dtstart": "future",
                    "description": "An upcoming event",
                },
                {
                    "uid": "event2",
                    "summary": "Past Event",
                    "dtstart": "past",
                    "description": "A past event",
                },
            ],
        )

        events = comparison.get_upcoming_events(ics_file)

        # Should only contain the future event
        assert len(events) == 1
        event_tuple = list(events)[0]
        assert event_tuple[0] == "event1"
        assert "Future Event" in event_tuple[2] or "An upcoming event" in event_tuple[2]

    def test_get_upcoming_events_empty_file(self, comparison, tmp_path):
        """Test getting upcoming events from empty ICS file."""
        ics_file = tmp_path / "empty.ics"
        self._create_ics_file(ics_file, [])

        events = comparison.get_upcoming_events(ics_file)

        assert len(events) == 0
        assert isinstance(events, set)

    def test_get_upcoming_events_all_past_events(self, comparison, tmp_path):
        """Test getting upcoming events when all events are in the past."""
        ics_file = tmp_path / "past.ics"
        self._create_ics_file(
            ics_file,
            [
                {"uid": "past1", "summary": "Event 1", "dtstart": "past"},
                {"uid": "past2", "summary": "Event 2", "dtstart": "past"},
            ],
        )

        events = comparison.get_upcoming_events(ics_file)

        assert len(events) == 0

    def test_get_upcoming_events_mixed_events(self, comparison, tmp_path):
        """Test getting upcoming events with mix of past and future."""
        ics_file = tmp_path / "mixed.ics"
        self._create_ics_file(
            ics_file,
            [
                {"uid": "past1", "summary": "Past", "dtstart": "past"},
                {"uid": "future1", "summary": "Future 1", "dtstart": "future"},
                {"uid": "future2", "summary": "Future 2", "dtstart": "future"},
                {"uid": "past2", "summary": "Past 2", "dtstart": "past"},
            ],
        )

        events = comparison.get_upcoming_events(ics_file)

        assert len(events) == 2
        uids = {event[0] for event in events}
        assert "future1" in uids
        assert "future2" in uids

    def test_get_upcoming_events_file_not_found(self, comparison, tmp_path):
        """Test error handling when ICS file doesn't exist."""
        non_existent = tmp_path / "nonexistent.ics"

        with pytest.raises(ICSReadError):
            comparison.get_upcoming_events(non_existent)

    def test_get_upcoming_events_invalid_ics_format(self, comparison, tmp_path):
        """Test error handling for corrupted ICS file."""
        ics_file = tmp_path / "invalid.ics"
        ics_file.write_text("This is not valid ICS content at all!")

        with pytest.raises(ICSReadError):
            comparison.get_upcoming_events(ics_file)

    def test_get_upcoming_events_malformed_ical(self, comparison, tmp_path):
        """Test handling of ICS file with processing errors."""
        ics_file = tmp_path / "malformed.ics"
        # Create a partially valid ICS file that fails on event processing
        ics_file.write_bytes(
            b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//Test//EN\r\n"
        )

        # Should raise ICSReadError for malformed ICS
        with pytest.raises(ICSReadError):
            comparison.get_upcoming_events(ics_file)

    def test_compare_calendars_identical(self, comparison, tmp_path):
        """Test comparing identical calendar directories."""
        old_dir = tmp_path / "old"
        new_dir = tmp_path / "new"
        old_dir.mkdir()
        new_dir.mkdir()

        # Create same files in both directories
        self._create_ics_file(
            old_dir / "calendar.ics",
            [
                {"uid": "event1", "summary": "Meeting", "dtstart": "future"},
            ],
        )
        self._create_ics_file(
            new_dir / "calendar.ics",
            [
                {"uid": "event1", "summary": "Meeting", "dtstart": "future"},
            ],
        )

        result = comparison.compare_calendars(old_dir, new_dir)

        assert result is False  # No differences

    def test_compare_calendars_different_events(self, comparison, tmp_path):
        """Test comparing calendars with different events."""
        old_dir = tmp_path / "old"
        new_dir = tmp_path / "new"
        old_dir.mkdir()
        new_dir.mkdir()

        self._create_ics_file(
            old_dir / "calendar.ics",
            [
                {"uid": "event1", "summary": "Meeting 1", "dtstart": "future"},
            ],
        )
        self._create_ics_file(
            new_dir / "calendar.ics",
            [
                {"uid": "event2", "summary": "Meeting 2", "dtstart": "future"},
            ],
        )

        result = comparison.compare_calendars(old_dir, new_dir)

        assert result is True  # Differences found

    def test_compare_calendars_different_times(self, comparison, tmp_path):
        """Test comparing calendars with same events at different times."""
        old_dir = tmp_path / "old"
        new_dir = tmp_path / "new"
        old_dir.mkdir()
        new_dir.mkdir()

        now = datetime.now(timezone.utc)

        # Create files with same event but different times
        self._create_ics_file(
            old_dir / "calendar.ics",
            [
                {
                    "uid": "event1",
                    "summary": "Meeting",
                    "dtstart": now + timedelta(hours=1),
                },
            ],
        )
        self._create_ics_file(
            new_dir / "calendar.ics",
            [
                {
                    "uid": "event1",
                    "summary": "Meeting",
                    "dtstart": now + timedelta(hours=2),
                },
            ],
        )

        result = comparison.compare_calendars(old_dir, new_dir)

        assert result is True  # Time difference detected

    def test_compare_calendars_empty_directories(self, comparison, tmp_path):
        """Test comparing empty calendar directories."""
        old_dir = tmp_path / "old"
        new_dir = tmp_path / "new"
        old_dir.mkdir()
        new_dir.mkdir()

        result = comparison.compare_calendars(old_dir, new_dir)

        assert result is False  # Both empty, no difference

    def test_compare_calendars_one_empty(self, comparison, tmp_path):
        """Test comparing when one directory is empty."""
        old_dir = tmp_path / "old"
        new_dir = tmp_path / "new"
        old_dir.mkdir()
        new_dir.mkdir()

        self._create_ics_file(
            new_dir / "calendar.ics",
            [
                {"uid": "event1", "summary": "Meeting", "dtstart": "future"},
            ],
        )

        result = comparison.compare_calendars(old_dir, new_dir)

        assert result is True  # Difference detected

    def test_compare_calendars_multiple_files(self, comparison, tmp_path):
        """Test comparing multiple ICS files in directories."""
        old_dir = tmp_path / "old"
        new_dir = tmp_path / "new"
        old_dir.mkdir()
        new_dir.mkdir()

        # Create multiple files in old dir
        self._create_ics_file(
            old_dir / "calendar1.ics",
            [
                {"uid": "event1", "summary": "Meeting 1", "dtstart": "future"},
            ],
        )
        self._create_ics_file(
            old_dir / "calendar2.ics",
            [
                {"uid": "event2", "summary": "Meeting 2", "dtstart": "future"},
            ],
        )

        # Create multiple files in new dir
        self._create_ics_file(
            new_dir / "calendar1.ics",
            [
                {"uid": "event1", "summary": "Meeting 1", "dtstart": "future"},
            ],
        )
        self._create_ics_file(
            new_dir / "calendar2.ics",
            [
                {"uid": "event2", "summary": "Meeting 2", "dtstart": "future"},
            ],
        )

        result = comparison.compare_calendars(old_dir, new_dir)

        assert result is False  # All events match

    def test_compare_calendars_nested_directories(self, comparison, tmp_path):
        """Test comparing calendars with nested directory structures."""
        old_dir = tmp_path / "old"
        new_dir = tmp_path / "new"
        old_dir.mkdir()
        new_dir.mkdir()

        # Create nested structure
        (old_dir / "team1").mkdir()
        (new_dir / "team1").mkdir()

        self._create_ics_file(
            old_dir / "team1" / "calendar.ics",
            [
                {"uid": "event1", "summary": "Match", "dtstart": "future"},
            ],
        )
        self._create_ics_file(
            new_dir / "team1" / "calendar.ics",
            [
                {"uid": "event1", "summary": "Match", "dtstart": "future"},
            ],
        )

        result = comparison.compare_calendars(old_dir, new_dir)

        assert result is False

    def test_compare_calendars_handles_read_errors(self, comparison, tmp_path):
        """Test that compare_calendars handles read errors gracefully."""
        old_dir = tmp_path / "old"
        new_dir = tmp_path / "new"
        old_dir.mkdir()
        new_dir.mkdir()

        # Create valid file in old
        self._create_ics_file(
            old_dir / "valid.ics",
            [
                {"uid": "event1", "summary": "Meeting", "dtstart": "future"},
            ],
        )

        # Create invalid file in old
        (old_dir / "invalid.ics").write_text("Invalid content")

        # Create valid file in new
        self._create_ics_file(
            new_dir / "valid.ics",
            [
                {"uid": "event1", "summary": "Meeting", "dtstart": "future"},
            ],
        )

        # Should not crash despite invalid file, just logs warning
        result = comparison.compare_calendars(old_dir, new_dir)

        assert isinstance(result, bool)

    def test_compare_calendars_past_events_ignored(self, comparison, tmp_path):
        """Test that past events are ignored in comparison."""
        old_dir = tmp_path / "old"
        new_dir = tmp_path / "new"
        old_dir.mkdir()
        new_dir.mkdir()

        # Same future event, different past events
        self._create_ics_file(
            old_dir / "calendar.ics",
            [
                {"uid": "future", "summary": "Meeting", "dtstart": "future"},
                {"uid": "past_old", "summary": "Old Past", "dtstart": "past"},
            ],
        )
        self._create_ics_file(
            new_dir / "calendar.ics",
            [
                {"uid": "future", "summary": "Meeting", "dtstart": "future"},
                {"uid": "past_new", "summary": "New Past", "dtstart": "past"},
            ],
        )

        result = comparison.compare_calendars(old_dir, new_dir)

        assert result is False  # Only future events matter

    def test_get_upcoming_events_returns_tuple_format(self, comparison, tmp_path):
        """Test that get_upcoming_events returns proper tuple format."""
        ics_file = tmp_path / "test.ics"
        self._create_ics_file(
            ics_file,
            [
                {
                    "uid": "test-id",
                    "summary": "Test Event",
                    "dtstart": "future",
                    "description": "Test Description",
                },
            ],
        )

        events = comparison.get_upcoming_events(ics_file)

        assert len(events) == 1
        event = list(events)[0]
        assert len(event) == 3
        assert isinstance(event, tuple)
        assert event[0] == "test-id"  # UID
        assert isinstance(event[1], str)  # DTSTART as string
        assert isinstance(event[2], str)  # DESCRIPTION as string
