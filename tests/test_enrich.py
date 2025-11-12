"""Tests for the enrich module."""

import yaml

from src.logic.enrich import apply_overrides, enrich_all


class TestApplyOverrides:
    """Tests for the apply_overrides function."""

    def test_apply_overrides_by_id(self, sample_fixtures, temp_yaml_file):
        """Test applying overrides by fixture ID."""
        overrides = {
            "2": {"tv": "BBC One"},
            "4": {"tv": "ITV"},
        }
        temp_yaml_file.write_text(yaml.safe_dump(overrides))

        applied = apply_overrides(sample_fixtures, temp_yaml_file)

        assert applied == 2
        assert sample_fixtures[1].tv == "BBC One"
        assert sample_fixtures[3].tv == "ITV"

    def test_apply_overrides_by_composite_key(self, sample_fixtures, temp_yaml_file):
        """Test applying overrides by composite key (date:home:away)."""
        overrides = {
            "2025-11-12:Arsenal:Manchester United": {"tv": "Amazon Prime"},
        }
        temp_yaml_file.write_text(yaml.safe_dump(overrides))

        applied = apply_overrides(sample_fixtures, temp_yaml_file)

        assert applied == 1
        assert sample_fixtures[1].tv == "Amazon Prime"

    def test_apply_overrides_file_not_exists(self, sample_fixtures, tmp_path):
        """Test that non-existent file returns 0 applied."""
        non_existent = tmp_path / "does_not_exist.yaml"
        applied = apply_overrides(sample_fixtures, non_existent)
        assert applied == 0

    def test_apply_overrides_empty_file(self, sample_fixtures, temp_yaml_file):
        """Test applying overrides from empty file."""
        temp_yaml_file.write_text("")
        applied = apply_overrides(sample_fixtures, temp_yaml_file)
        assert applied == 0

    def test_apply_overrides_no_tv_value(self, sample_fixtures, temp_yaml_file):
        """Test that overrides without TV value are skipped."""
        overrides = {
            "1": {"other_field": "value"},
        }
        temp_yaml_file.write_text(yaml.safe_dump(overrides))

        original_tv = sample_fixtures[0].tv
        applied = apply_overrides(sample_fixtures, temp_yaml_file)

        assert applied == 0
        assert sample_fixtures[0].tv == original_tv

    def test_apply_overrides_replaces_existing_tv(
        self, sample_fixtures, temp_yaml_file
    ):
        """Test that overrides replace existing TV info."""
        overrides = {
            "1": {"tv": "New Broadcaster"},
        }
        temp_yaml_file.write_text(yaml.safe_dump(overrides))

        applied = apply_overrides(sample_fixtures, temp_yaml_file)

        # Should be 0 because fixture already had TV info
        assert applied == 0
        assert sample_fixtures[0].tv == "New Broadcaster"


class TestEnrichAll:
    """Tests for the enrich_all function."""

    def test_enrich_all_with_overrides(self, sample_fixtures, temp_yaml_file):
        """Test enrich_all with overrides only."""
        overrides = {
            "2": {"tv": "BBC Two"},
        }
        temp_yaml_file.write_text(yaml.safe_dump(overrides))

        result = enrich_all(
            sample_fixtures,
            club_ics_url=None,
            overrides_path=temp_yaml_file,
        )

        assert result["tv_before"] == 2
        assert result["tv_after"] == 3
        assert result["tv_overrides_applied"] == 1

    def test_enrich_all_no_changes(self, sample_fixtures):
        """Test enrich_all with no sources makes no changes."""
        result = enrich_all(
            sample_fixtures,
            club_ics_url=None,
            overrides_path=None,
        )

        assert result["tv_before"] == 2
        assert result["tv_after"] == 2

    def test_enrich_all_invalid_overrides_path(self, sample_fixtures, tmp_path):
        """Test enrich_all handles invalid overrides path gracefully."""
        non_existent = tmp_path / "missing.yaml"

        result = enrich_all(
            sample_fixtures,
            club_ics_url=None,
            overrides_path=non_existent,
        )

        # Should not crash, just log warning
        assert result["tv_before"] == 2
        assert result["tv_after"] == 2
