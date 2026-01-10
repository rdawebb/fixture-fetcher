"""Tests for the snapshot module."""

from datetime import datetime, timezone

import pytest

from backend.storage.snapshot import (
    _dict_to_key_fields,
    _fixture_to_dict,
    diff_changes,
    load_snapshot,
    save_snapshot,
)
from logic.fixtures.models import Fixture


class TestFixtureToDict:
    """Tests for _fixture_to_dict function."""

    def test_fixture_to_dict_with_kickoff(self, fixture_with_all_fields):
        """Test converting fixture with kickoff time to dict."""
        result = _fixture_to_dict(fixture_with_all_fields)

        assert result["id"] == "1"
        assert result["home_team"] == "Team A"
        assert result["away_team"] == "Team B"
        assert result["utc_kickoff"] == "2025-11-15T15:00:00+00:00"
        assert result["venue"] == "Stadium A"
        assert result["status"] == "SCHEDULED"

    def test_fixture_to_dict_without_kickoff(self, fixture_without_optional_fields):
        """Test converting fixture without kickoff time to dict."""
        result = _fixture_to_dict(fixture_without_optional_fields)

        assert result["id"] == "2"
        assert result["utc_kickoff"] is None
        assert result["venue"] is None


class TestDictToKeyFields:
    """Tests for _dict_to_key_fields function."""

    @pytest.mark.parametrize(
        "fixture_dict,expected",
        [
            (
                {
                    "utc_kickoff": "2025-11-15T15:00:00+00:00",
                    "venue": "Stadium A",
                    "tv": "Sky Sports",
                    "status": "SCHEDULED",
                },
                ("2025-11-15T15:00:00+00:00", "Stadium A", "Sky Sports", "SCHEDULED"),
            ),
            (
                {
                    "utc_kickoff": None,
                    "venue": None,
                    "status": "SCHEDULED",
                },
                ("", "", "", "SCHEDULED"),
            ),
            (
                {},
                ("", "", "", ""),
            ),
        ],
    )
    def test_dict_to_key_fields(self, fixture_dict, expected):
        """Test extracting key fields from fixture dict."""
        result = _dict_to_key_fields(fixture_dict)
        assert result == expected


class TestSaveSnapshot:
    """Tests for save_snapshot function."""

    def test_save_snapshot_creates_file(self, fixture_with_all_fields, tmp_path):
        """Test that save_snapshot creates a JSON file."""
        snapshot_path = tmp_path / "snapshot.json"

        save_snapshot([fixture_with_all_fields], snapshot_path)

        assert snapshot_path.exists()
        content = snapshot_path.read_text()
        assert '"1"' in content
        assert "Team A" in content

    def test_save_snapshot_creates_parent_directory(
        self, fixture_with_all_fields, tmp_path
    ):
        """Test that save_snapshot creates parent directories."""
        snapshot_path = tmp_path / "nested" / "dir" / "snapshot.json"

        save_snapshot([fixture_with_all_fields], snapshot_path)

        assert snapshot_path.exists()
        assert snapshot_path.parent.exists()

    def test_save_snapshot_multiple_fixtures(
        self, fixture_with_all_fields, fixture_without_optional_fields, tmp_path
    ):
        """Test saving multiple fixtures to snapshot."""
        snapshot_path = tmp_path / "snapshot.json"

        save_snapshot(
            [fixture_with_all_fields, fixture_without_optional_fields],
            snapshot_path,
        )

        import json

        content = json.loads(snapshot_path.read_text())
        assert len(content) == 2
        assert "1" in content
        assert "2" in content


class TestLoadSnapshot:
    """Tests for load_snapshot function."""

    def test_load_snapshot_success(self, fixture_with_all_fields, tmp_path):
        """Test loading snapshot from file."""
        snapshot_path = tmp_path / "snapshot.json"
        save_snapshot([fixture_with_all_fields], snapshot_path)

        result = load_snapshot(snapshot_path)

        assert "1" in result
        assert result["1"]["home_team"] == "Team A"
        assert result["1"]["away_team"] == "Team B"

    def test_load_snapshot_file_not_exists(self, tmp_path):
        """Test loading snapshot when file doesn't exist."""
        snapshot_path = tmp_path / "nonexistent.json"

        result = load_snapshot(snapshot_path)

        assert result == {}

    def test_load_snapshot_invalid_json(self, tmp_path):
        """Test loading snapshot with invalid JSON."""
        snapshot_path = tmp_path / "invalid.json"
        snapshot_path.write_text("{ invalid json }")

        result = load_snapshot(snapshot_path)

        assert result == {}


class TestDiffChanges:
    """Tests for diff_changes function."""

    def test_diff_changes_no_changes(
        self, fixture_with_all_fields, snapshot_from_fixture
    ):
        """Test diffing when fixtures haven't changed."""
        result = diff_changes([fixture_with_all_fields], snapshot_from_fixture)

        assert result == {"time": 0, "venue": 0, "tv": 0, "status": 0}

    def test_diff_changes_kickoff_time_changed(
        self, fixture_with_different_time, snapshot_from_fixture
    ):
        """Test diffing when kickoff time changed."""
        result = diff_changes([fixture_with_different_time], snapshot_from_fixture)

        assert result["time"] == 1
        assert result["venue"] == 0
        assert result["status"] == 0

    def test_diff_changes_venue_changed(
        self, fixture_with_different_venue, snapshot_from_fixture
    ):
        """Test diffing when venue changed."""
        result = diff_changes([fixture_with_different_venue], snapshot_from_fixture)

        assert result["time"] == 0
        assert result["venue"] == 1
        assert result["status"] == 0

    def test_diff_changes_status_changed(
        self, fixture_with_different_status, snapshot_from_fixture
    ):
        """Test diffing when status changed."""
        result = diff_changes([fixture_with_different_status], snapshot_from_fixture)

        assert result["time"] == 0
        assert result["venue"] == 0
        assert result["status"] == 1

    def test_diff_changes_multiple_changes(
        self, fixture_with_all_fields, snapshot_from_fixture, tmp_path
    ):
        """Test diffing when multiple properties changed."""
        new_fixture = Fixture(
            id="1",
            competition="Premier League",
            competition_code="PL",
            matchday=1,
            utc_kickoff=datetime(2025, 11, 15, 16, 0, 0, tzinfo=timezone.utc),
            home_team="Team A",
            away_team="Team B",
            venue="Stadium B",
            status="FINISHED",
            tv="Sky Sports",
            is_home=True,
        )

        result = diff_changes([new_fixture], snapshot_from_fixture)

        assert result["time"] == 1
        assert result["venue"] == 1
        assert result["status"] == 1

    def test_diff_changes_fixture_not_in_snapshot(self, fixture_with_all_fields):
        """Test diffing when fixture is not in snapshot."""
        snapshot = {}

        result = diff_changes([fixture_with_all_fields], snapshot)

        assert result == {"time": 0, "venue": 0, "tv": 0, "status": 0}
