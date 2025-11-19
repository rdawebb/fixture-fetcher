"""Tests for the filters module."""

from datetime import datetime, timezone

import pytest

from logic.fixtures.filters import Filter
from utils.errors import DataProcessingError, InvalidInputError


class TestFilter:
    """Tests for the Filter class."""

    def test_only_home(self, sample_fixtures):
        """Test filtering only home fixtures."""
        result = Filter.only_home(sample_fixtures)
        assert len(result) == 2
        assert all(f.is_home for f in result)

    def test_only_away(self, sample_fixtures):
        """Test filtering only away fixtures."""
        result = Filter.only_away(sample_fixtures)
        assert len(result) == 2
        assert all(not f.is_home for f in result)

    def test_only_scheduled(self, sample_fixtures):
        """Test filtering only scheduled fixtures."""
        result = Filter.only_scheduled(sample_fixtures)
        assert len(result) == 3
        assert all(f.status in ("SCHEDULED", "TIMED") for f in result)

    def test_only_televised(self, sample_fixtures):
        """Test filtering only televised fixtures."""
        result = Filter.only_televised(sample_fixtures)
        assert len(result) == 2
        assert all(f.tv is not None for f in result)

    def test_by_competition(self, sample_fixtures):
        """Test filtering by competition code."""
        result = Filter.by_competition(sample_fixtures, "PL")
        assert len(result) == 2
        assert all(f.competition_code == "PL" for f in result)

    def test_by_competition_invalid_code(self, sample_fixtures):
        """Test filtering with invalid competition code."""
        with pytest.raises(InvalidInputError):
            Filter.by_competition(sample_fixtures, None)  # type: ignore

    def test_by_date_range(self, sample_fixtures):
        """Test filtering by date range."""
        start_date = datetime(2025, 11, 11, 0, 0, 0, tzinfo=timezone.utc)
        end_date = datetime(2025, 11, 13, 23, 59, 59, tzinfo=timezone.utc)

        result = Filter.by_date_range(sample_fixtures, start_date, end_date)
        assert len(result) == 1
        assert result[0].id == "2"

    def test_by_date_range_invalid_dates(self, sample_fixtures):
        """Test filtering with invalid date types."""
        with pytest.raises(InvalidInputError):
            Filter.by_date_range(sample_fixtures, "2025-11-11", "2025-11-13")  # type: ignore

    def test_apply_filters_multiple(self, sample_fixtures):
        """Test applying multiple filters at once."""
        result = Filter.apply_filters(
            sample_fixtures,
            scheduled_only=True,
            home_only=True,
        )
        assert len(result) == 2
        assert all(f.is_home and f.status in ("SCHEDULED", "TIMED") for f in result)

    def test_apply_filters_no_filters(self, sample_fixtures):
        """Test applying no filters returns all fixtures."""
        result = Filter.apply_filters(sample_fixtures)
        assert len(result) == len(sample_fixtures)

    def test_empty_fixture_list(self):
        """Test filtering empty fixture list."""
        result = Filter.only_home([])
        assert len(result) == 0

    def test_filter_with_bad_data(self):
        """Test filter handles invalid fixture data gracefully."""
        bad_fixtures = [{"not": "a fixture"}]
        with pytest.raises(DataProcessingError):
            Filter.only_home(bad_fixtures)  # type: ignore
