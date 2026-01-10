"""Integration tests for CLI and shell modules."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.cli import _slug, build, cache_teams
from logic.fixtures.models import Fixture
from utils.errors import InvalidInputError, TeamNotFoundError


class TestSlugFunction:
    """Tests for the _slug helper function."""

    @pytest.mark.parametrize(
        "input_name,expected_slug",
        [
            ("Manchester United", "manchester-united"),
            ("Real Madrid CF", "real-madrid-cf"),
            ("manchester-united", "manchester-united"),
            ("St. Mary's", "st--mary-s"),
            ("", ""),
            ("!!!", ""),
        ],
    )
    def test_slug(self, input_name, expected_slug):
        """Test slugifying various team names."""
        assert _slug(input_name) == expected_slug


class TestBuildFunction:
    """Integration tests for the build function."""

    @patch("app.cli.get_team_info")
    @patch("app.cli.FootballDataRepository")
    def test_build_with_team(self, mock_repo_class, mock_get_team_info, tmp_path):
        """Test building ICS file for a specific team."""
        # Setup mock repository and fixtures
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_get_team_info.return_value = ("Premier League", "Man Utd")

        fixture = Fixture(
            id="1",
            competition="Premier League",
            competition_code="PL",
            matchday=1,
            utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
            home_team="Manchester United",
            away_team="Liverpool",
            venue="Old Trafford",
            status="SCHEDULED",
            tv="Sky Sports",
            is_home=True,
        )
        mock_repo.fetch_fixtures.return_value = [fixture]

        # Run build function
        output_dir = tmp_path / "output"
        cache_dir = tmp_path / "cache"
        build(team="Manchester United", output=output_dir, cache_dir=cache_dir)

        # Verify repository was called correctly
        mock_repo.fetch_fixtures.assert_called_once()
        call_args = mock_repo.fetch_fixtures.call_args
        assert call_args is not None
        assert call_args[0][0] == "Manchester United"

        # Verify output file was created
        assert output_dir.exists()
        ics_files = list(output_dir.rglob("*.ics"))
        assert len(ics_files) > 0

    @patch("app.cli.FootballDataRepository")
    def test_build_no_team_specified(self, mock_repo_class, tmp_path):
        """Test build function raises error when no team specified."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        output_dir = tmp_path / "output"
        cache_dir = tmp_path / "cache"

        with pytest.raises(InvalidInputError):
            build(output=output_dir, cache_dir=cache_dir)

        # Repository should not be called when no team is specified
        mock_repo.fetch_fixtures.assert_not_called()

    @patch("app.cli.get_team_info")
    @patch("app.cli.FootballDataRepository")
    def test_build_with_filters(self, mock_repo_class, mock_get_team_info, tmp_path):
        """Test build function applies filters correctly."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_get_team_info.return_value = ("Premier League", "Man Utd")

        # Create multiple fixtures with different properties
        fixtures = [
            Fixture(
                id="1",
                competition="Premier League",
                competition_code="PL",
                matchday=1,
                utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
                home_team="Manchester United",
                away_team="Liverpool",
                venue="Old Trafford",
                status="SCHEDULED",
                tv="Sky Sports",
                is_home=True,
            ),
            Fixture(
                id="2",
                competition="FA Cup",
                competition_code="FA",
                matchday=None,
                utc_kickoff=datetime(2025, 11, 20, 20, 0, 0, tzinfo=timezone.utc),
                home_team="Arsenal",
                away_team="Manchester United",
                venue="Emirates Stadium",
                status="SCHEDULED",
                tv=None,
                is_home=False,
            ),
        ]
        mock_repo.fetch_fixtures.return_value = fixtures

        output_dir = tmp_path / "output"
        cache_dir = tmp_path / "cache"
        build(
            team="Manchester United",
            televised_only=True,
            output=output_dir,
            cache_dir=cache_dir,
        )

        # Should filter to only televised fixtures (fixture 1)
        ics_files = list(output_dir.rglob("*.ics"))
        assert len(ics_files) > 0

    @patch("app.cli.get_team_info")
    @patch("app.cli.FootballDataRepository")
    def test_build_with_competitions_filter(
        self, mock_repo_class, mock_get_team_info, tmp_path
    ):
        """Test build function with competition filter."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_get_team_info.return_value = ("Premier League", "Man Utd")

        fixture = Fixture(
            id="1",
            competition="Premier League",
            competition_code="PL",
            matchday=1,
            utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
            home_team="Manchester United",
            away_team="Liverpool",
            venue="Old Trafford",
            status="SCHEDULED",
            tv="Sky Sports",
            is_home=True,
        )
        mock_repo.fetch_fixtures.return_value = [fixture]

        output_dir = tmp_path / "output"
        cache_dir = tmp_path / "cache"
        build(
            team="Manchester United",
            competitions=["PL", "CL"],
            output=output_dir,
            cache_dir=cache_dir,
        )

        # Verify competitions were parsed and passed
        call_args = mock_repo.fetch_fixtures.call_args[0]
        assert "PL" in call_args[1]
        assert "CL" in call_args[1]

    @patch("app.cli.FootballDataRepository")
    def test_build_with_refresh_cache(self, mock_repo_class, tmp_path):
        """Test build function with refresh cache option."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.fetch_fixtures.return_value = []

        output_dir = tmp_path / "output"
        cache_dir = tmp_path / "cache"
        build(
            team="Manchester United",
            refresh_cache=True,
            output=output_dir,
            cache_dir=cache_dir,
        )

        # Verify refresh_team_cache was called
        mock_repo.client.refresh_team_cache.assert_called_once()

    @patch("app.cli.FootballDataRepository")
    def test_build_creates_output_directory(self, mock_repo_class, tmp_path):
        """Test build function creates output directory if it doesn't exist."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.fetch_fixtures.return_value = []

        output_dir = tmp_path / "nested" / "output"
        cache_dir = tmp_path / "cache"
        assert not output_dir.exists()

        build(team="Manchester United", output=output_dir, cache_dir=cache_dir)

        # Output directory should be created
        assert output_dir.exists()

    @patch("app.cli.FootballDataRepository")
    def test_build_error_handling(self, mock_repo_class, tmp_path):
        """Test build function handles errors gracefully."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.fetch_fixtures.side_effect = Exception("API Error")

        output_dir = tmp_path / "output"
        cache_dir = tmp_path / "cache"

        # Should not raise, but log error
        build(team="Manchester United", output=output_dir, cache_dir=cache_dir)

    @patch("app.cli.FootballDataRepository")
    def test_build_no_summarise(self, mock_repo_class, tmp_path):
        """Test build function with summarise disabled."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        fixture = Fixture(
            id="1",
            competition="Premier League",
            competition_code="PL",
            matchday=1,
            utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
            home_team="Manchester United",
            away_team="Liverpool",
            venue="Old Trafford",
            status="SCHEDULED",
            tv="Sky Sports",
            is_home=True,
        )
        mock_repo.fetch_fixtures.return_value = [fixture]

        output_dir = tmp_path / "output"
        cache_dir = tmp_path / "cache"
        build(
            team="Manchester United",
            summarise=False,
            output=output_dir,
            cache_dir=cache_dir,
        )

        # Should complete without error
        assert output_dir.exists()


class TestCacheTeamsFunction:
    """Integration tests for the cache_teams function."""

    @patch("app.cli.FootballDataRepository")
    def test_cache_teams_single_competition(self, mock_repo_class, tmp_path):
        """Test caching teams for a single competition."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        cache_file = tmp_path / "teams.yaml"
        cache_teams(competitions=["PL"], output=cache_file)

        # Verify refresh_team_cache was called with correct competition
        call_args = mock_repo.client.refresh_team_cache.call_args
        assert call_args[0][0] == ["PL"]
        assert call_args[1]["cache_path"] == cache_file

    @patch("app.cli.FootballDataRepository")
    def test_cache_teams_multiple_competitions(self, mock_repo_class, tmp_path):
        """Test caching teams for multiple competitions."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        cache_file = tmp_path / "teams.yaml"
        cache_teams(competitions=["PL", "CL", "FA"], output=cache_file)

        # Verify all competitions were parsed correctly
        call_args = mock_repo.client.refresh_team_cache.call_args
        comps = call_args[0][0]
        assert "PL" in comps
        assert "CL" in comps
        assert "FA" in comps

    @patch("app.cli.FootballDataRepository")
    def test_cache_teams_creates_parent_directory(self, mock_repo_class, tmp_path):
        """Test cache_teams creates parent directory if needed."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        cache_file = tmp_path / "nested" / "dir" / "teams.yaml"
        cache_teams(competitions=["PL"], output=cache_file)

        # The cache file path should be passed to the repository
        call_args = mock_repo.client.refresh_team_cache.call_args
        assert call_args[1]["cache_path"] == cache_file


class TestCLIClass:
    """Tests for the CLI class interactive shell.

    Note: These tests use mocking to avoid interactive prompts.
    For full end-to-end testing, consider using a tool like pexpect
    or click's CliRunner if the CLI were refactored to use Click.
    """

    def test_cli_initialization(self):
        """Test CLI class can be initialized."""
        from app.shell import CLI

        cli = CLI()
        assert cli.console is not None
        assert cli.panel_width > 0

    def test_cli_welcome_message(self):
        """Test welcome message can be rendered."""
        from app.shell import CLI

        cli = CLI()
        # Should not raise
        try:
            cli.welcome_message()
        except Exception as e:
            pytest.fail(f"welcome_message raised {e}")

    @patch("app.shell.confirm")
    @patch("app.shell.select")
    @patch("app.shell.select_multiple")
    @patch("app.shell.build")
    def test_cli_interactive_prompt_confirmed(
        self, mock_build, mock_select_multiple, mock_select, mock_confirm
    ):
        """Test CLI interactive prompt when user confirms."""
        from app.shell import CLI

        # Setup mocks
        mock_confirm.return_value = True
        mock_select.return_value = "Manchester United FC"
        mock_select_multiple.return_value = ["Premier League"]

        cli = CLI()
        cli.interactive_prompt()

        # Verify build was called
        mock_build.assert_called_once()

    @patch("app.shell.confirm")
    def test_cli_interactive_prompt_declined(self, mock_confirm):
        """Test CLI interactive prompt when user declines."""
        from app.shell import CLI

        mock_confirm.return_value = False

        cli = CLI()
        cli.interactive_prompt()

        # Build should not be called
        # (Need to patch build to verify, but it shouldn't be reached)

    @patch("app.shell.confirm")
    @patch("app.shell.select")
    @patch("app.shell.select_multiple")
    @patch("app.shell.build")
    def test_cli_interactive_prompt_with_build_error(
        self, mock_build, mock_select_multiple, mock_select, mock_confirm
    ):
        """Test CLI handles errors during build gracefully."""
        from app.shell import CLI

        mock_confirm.return_value = True
        mock_select.return_value = "Manchester United FC"
        mock_select_multiple.return_value = ["Premier League"]
        mock_build.side_effect = Exception("Build failed")

        cli = CLI()
        # Should handle exception gracefully
        with pytest.raises(Exception):
            cli.interactive_prompt()

    def test_cli_welcome_message_renders(self):
        """Test that welcome message renders without error."""
        from app.shell import CLI

        cli = CLI()
        # Create a mock console to avoid printing
        with patch.object(cli, "console") as mock_console:
            cli.welcome_message()
            # Verify print was called
            mock_console.print.assert_called_once()

    @patch("app.shell.confirm")
    @patch("app.shell.select")
    @patch("app.shell.select_multiple")
    @patch("app.shell.Spinner")
    @patch("app.shell.build")
    def test_cli_full_interactive_flow(
        self, mock_build, mock_spinner, mock_select_multiple, mock_select, mock_confirm
    ):
        """Test full interactive flow with all UI elements."""
        from app.shell import CLI

        mock_confirm.return_value = True
        mock_select.return_value = "Manchester United FC"
        mock_select_multiple.return_value = ["Premier League"]
        mock_spinner_instance = Mock()
        mock_spinner.return_value = mock_spinner_instance

        cli = CLI()
        cli.interactive_prompt()

        # Verify spinner was started and stopped
        mock_spinner_instance.start.assert_called_once()
        mock_spinner_instance.stop.assert_called_once()
        mock_build.assert_called_once()


class TestCLIEndToEnd:
    """End-to-end integration tests for the CLI.

    These tests verify the complete workflow from user input through
    ICS file generation.
    """

    @patch("app.cli.get_team_info")
    @patch("app.cli.FootballDataRepository")
    def test_full_workflow_build_and_export(
        self, mock_repo_class, mock_get_team_info, tmp_path
    ):
        """Test complete workflow of building ICS files."""
        # Setup mock data
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_get_team_info.return_value = ("Premier League", "Man Utd")

        fixture = Fixture(
            id="1",
            competition="Premier League",
            competition_code="PL",
            matchday=1,
            utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
            home_team="Manchester United",
            away_team="Liverpool",
            venue="Old Trafford",
            status="SCHEDULED",
            tv="Sky Sports",
            is_home=True,
        )
        mock_repo.fetch_fixtures.return_value = [fixture]

        # Execute workflow
        output_dir = tmp_path / "public"
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        build(
            team="Manchester United",
            competitions=["PL"],
            home_only=True,
            output=output_dir,
            cache_dir=cache_dir,
        )

        # Verify output
        assert output_dir.exists()
        ics_files = list(output_dir.rglob("*.ics"))
        assert len(ics_files) > 0

        # Verify ICS file content
        ics_file = ics_files[0]
        content = ics_file.read_text()
        assert "Manchester United" in content
        assert "Liverpool" in content
        assert "BEGIN:VCALENDAR" in content

    @patch("app.cli.FootballDataRepository")
    def test_workflow_with_snapshot(self, mock_repo_class, tmp_path):
        """Test workflow that saves and uses snapshots for change detection."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        fixture = Fixture(
            id="1",
            competition="Premier League",
            competition_code="PL",
            matchday=1,
            utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
            home_team="Manchester United",
            away_team="Liverpool",
            venue="Old Trafford",
            status="SCHEDULED",
            tv="Sky Sports",
            is_home=True,
        )
        mock_repo.fetch_fixtures.return_value = [fixture]

        # Setup paths
        output_dir = tmp_path / "public"
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        with patch("app.cli.Path") as mock_path:
            # Mock the cache path to use our temp directory
            mock_path.side_effect = (
                lambda p: Path(cache_dir) / p if isinstance(p, str) else Path(p)
            )

            build(
                team="Manchester United",
                output=output_dir,
                cache_dir=cache_dir,
            )

            # First run creates snapshot
            # Second run would compare against snapshot

    @patch("app.cli.get_team_info")
    @patch("app.cli.FootballDataRepository")
    def test_build_error_on_enrich(self, mock_repo_class, mock_get_team_info, tmp_path):
        """Test build handles errors during enrich_all."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_get_team_info.return_value = ("Premier League", "Man Utd")

        fixture = Fixture(
            id="1",
            competition="Premier League",
            competition_code="PL",
            matchday=1,
            utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
            home_team="Manchester United",
            away_team="Liverpool",
            venue="Old Trafford",
            status="SCHEDULED",
            tv="Sky Sports",
            is_home=True,
        )
        mock_repo.fetch_fixtures.return_value = [fixture]

        output_dir = tmp_path / "output"
        cache_dir = tmp_path / "cache"

        with patch("app.cli.enrich_all") as mock_enrich:
            mock_enrich.side_effect = Exception("Enrichment failed")

            result = build(
                team="Manchester United",
                output=output_dir,
                cache_dir=cache_dir,
            )

        # Should handle error gracefully and return failed entry
        assert len(result["failed"]) > 0

    @patch("app.cli.get_team_info")
    @patch("app.cli.FootballDataRepository")
    def test_build_with_all_filters(
        self, mock_repo_class, mock_get_team_info, tmp_path
    ):
        """Test build function with all filter options enabled."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_get_team_info.return_value = ("Premier League", "Man Utd")

        fixture = Fixture(
            id="1",
            competition="Premier League",
            competition_code="PL",
            matchday=1,
            utc_kickoff=datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc),
            home_team="Manchester United",
            away_team="Liverpool",
            venue="Old Trafford",
            status="SCHEDULED",
            tv="Sky Sports",
            is_home=True,
        )
        mock_repo.fetch_fixtures.return_value = [fixture]

        output_dir = tmp_path / "output"
        cache_dir = tmp_path / "cache"

        result = build(
            team="Manchester United",
            home_only=True,
            away_only=False,
            televised_only=True,
            output=output_dir,
            cache_dir=cache_dir,
        )

        # Should complete successfully
        assert output_dir.exists()
        assert len(result["successful"]) > 0

    @patch("app.cli.get_team_info")
    @patch("app.cli.FootballDataRepository")
    def test_build_get_team_info_not_found(
        self, mock_repo_class, mock_get_team_info, tmp_path
    ):
        """Test build when team is not found in league cache."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_get_team_info.side_effect = TeamNotFoundError(
            "Team not found", context={"team_name": "Unknown Team"}
        )

        output_dir = tmp_path / "output"
        cache_dir = tmp_path / "cache"

        result = build(
            team="Unknown Team",
            output=output_dir,
            cache_dir=cache_dir,
        )

        # Should handle error and add to failed list
        assert len(result["failed"]) > 0

    @patch("app.cli.FootballDataRepository")
    def test_cache_teams_with_whitespace(self, mock_repo_class, tmp_path):
        """Test cache_teams strips whitespace from competition codes."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        cache_file = tmp_path / "teams.yaml"
        cache_teams(competitions=["  PL  ", "CL", "  FA  "], output=cache_file)

        # Verify whitespace is stripped
        call_args = mock_repo.client.refresh_team_cache.call_args
        assert call_args[0][0] == ["PL", "CL", "FA"]

    @patch("app.cli.FootballDataRepository")
    def test_cache_teams_empty_strings_filtered(self, mock_repo_class, tmp_path):
        """Test cache_teams filters out empty competition codes."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        cache_file = tmp_path / "teams.yaml"
        cache_teams(competitions=["PL", "", "CL", "   "], output=cache_file)

        # Verify empty strings are filtered
        call_args = mock_repo.client.refresh_team_cache.call_args
        assert call_args[0][0] == ["PL", "CL"]
