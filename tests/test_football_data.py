"""Tests for Football Data API client."""

from unittest.mock import patch

import pytest
import yaml

from backend.api.football_data import COMP_CODES, FDClient
from utils.errors import (
    AuthenticationError,
    ConnectionError,
    NotFoundError,
    ParsingError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
    TimeoutError,
)


class TestFDClientInitialisation:
    """Tests for FDClient initialisation."""

    @patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_client_initialisation_success(self):
        """Test successful client initialisation."""
        client = FDClient()
        assert client.token == {"X-Auth-Token": "test_token"}
        assert client.session is not None

    @patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", None)
    def test_client_initialisation_no_token(self):
        """Test that initialisation fails without token."""
        with pytest.raises(AuthenticationError):
            FDClient()


class TestFDClientCache:
    """Tests for FDClient cache operations."""

    def test_load_cache_success(self, mock_cache_path):
        """Test loading cache from file."""
        cache_data = {
            "Premier League": {
                "Manchester United": {"id": 66, "short_name": "Man Utd"},
                "Liverpool": {"id": 64, "short_name": "Liverpool"},
            }
        }
        mock_cache_path.write_text(yaml.safe_dump(cache_data))

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            assert client.cache == cache_data

    def test_load_cache_file_not_exists(self, mock_cache_path):
        """Test loading cache when file doesn't exist."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            assert client.cache == {}

    def test_save_cache(self, mock_cache_path):
        """Test saving cache to file."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            client.cache = {
                "Premier League": {
                    "Team A": {"id": 1, "short_name": "TAM"},
                    "Team B": {"id": 2, "short_name": "TMB"},
                }
            }
            client._save_cache()

            assert mock_cache_path.exists()
            loaded_data = yaml.safe_load(mock_cache_path.read_text())
            assert loaded_data == {
                "Premier League": {
                    "Team A": {"id": 1, "short_name": "TAM"},
                    "Team B": {"id": 2, "short_name": "TMB"},
                }
            }

    def test_add_to_cache(self, mock_cache_path):
        """Test adding team to cache."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            client._add_to_cache("Premier League", "Chelsea", 61, "CHE")

            assert client.cache["Premier League"]["Chelsea"]["id"] == 61
            assert client.cache["Premier League"]["Chelsea"]["short_name"] == "CHE"
            assert mock_cache_path.exists()


class TestFDClientHandleResponse:
    """Tests for FDClient response handling."""

    @patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_success(self, mock_api_response):
        """Test handling successful response."""
        client = FDClient()
        mock_response = mock_api_response(200, {"data": "value"})

        result = client._handle_response(mock_response, "test context")
        assert result == {"data": "value"}

    @pytest.mark.parametrize(
        "status_code,exception_class",
        [
            (404, NotFoundError),
            (429, RateLimitError),
            (500, ServerError),
            (503, ServiceUnavailableError),
            (400, Exception),  # Will be UnknownAPIError
            (502, ServerError),
        ],
    )
    @patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_error_codes(
        self, status_code, exception_class, mock_api_response
    ):
        """Test handling various error response codes."""
        from utils.errors import UnknownAPIError

        client = FDClient()
        mock_response = mock_api_response(status_code)

        # Handle UnknownAPIError separately since it's used for 400
        if status_code == 400:
            with pytest.raises(UnknownAPIError):
                client._handle_response(mock_response, "test context")
        else:
            with pytest.raises(exception_class):
                client._handle_response(mock_response, "test context")

    @patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_invalid_json(self, mock_api_response):
        """Test handling response with invalid JSON."""
        client = FDClient()
        mock_response = mock_api_response(200, side_effect=ValueError("Invalid JSON"))

        with pytest.raises(ParsingError):
            client._handle_response(mock_response, "test context")

    @patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_non_dict_json(self, mock_api_response):
        """Test handling response with non-dict JSON."""
        client = FDClient()
        mock_response = mock_api_response(200, ["not", "a", "dict"])

        with pytest.raises(ParsingError):
            client._handle_response(mock_response, "test context")


class TestFDClientRefreshCache:
    """Tests for FDClient cache refresh."""

    def test_refresh_team_cache_success(self, mock_cache_path, mock_api_response):
        """Test successful team cache refresh."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            mock_response = mock_api_response(
                200,
                {
                    "teams": [
                        {"name": "Team A", "id": 1, "shortName": "TA"},
                        {"name": "Team B", "id": 2, "shortName": "TB"},
                    ]
                },
            )

            with patch.object(client.session, "get", return_value=mock_response):
                client.refresh_team_cache(competitions=["PL"])

            assert "Team A" in client.cache["Premier League"]
            assert client.cache["Premier League"]["Team A"]["id"] == 1
            assert client.cache["Premier League"]["Team A"]["short_name"] == "TA"
            assert mock_cache_path.exists()

    def test_refresh_team_cache_all_competitions(
        self, mock_cache_path, mock_api_response
    ):
        """Test refreshing cache for all competitions."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            mock_response = mock_api_response(200, {"teams": []})

            with patch.object(
                client.session, "get", return_value=mock_response
            ) as mock_get:
                # Should default to all competition codes
                client.refresh_team_cache()

            # Should have made calls for all default competitions
            assert mock_get.call_count == len(COMP_CODES)


class TestFDClientGetTeamId:
    """Tests for FDClient get_team_id_by_name method."""

    def test_get_team_id_from_cache(self, cache_with_teams):
        """Test getting team ID from cache."""
        result = cache_with_teams.get_team_id_by_name("Manchester United")
        assert result == 66

    def test_get_team_id_case_insensitive_cache(self, cache_with_teams):
        """Test getting team ID from cache is case-insensitive."""
        result = cache_with_teams.get_team_id_by_name("manchester united")
        assert result == 66

    def test_get_team_id_from_api(
        self, mock_cache_path, mock_api_response, sample_team_data
    ):
        """Test getting team ID from API when not in cache."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            mock_response = mock_api_response(200, {"teams": [sample_team_data]})

            with patch.object(client.session, "get", return_value=mock_response):
                result = client.get_team_id_by_name("Manchester United")

            assert result == 66

    def test_get_team_id_by_short_name(
        self, mock_cache_path, mock_api_response, sample_team_data
    ):
        """Test getting team ID by short name."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            mock_response = mock_api_response(200, {"teams": [sample_team_data]})

            with patch.object(client.session, "get", return_value=mock_response):
                result = client.get_team_id_by_name("Man Utd")

            assert result == 66

    def test_get_team_id_not_found(self, mock_cache_path, mock_api_response):
        """Test NotFoundError when team not found."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            mock_response = mock_api_response(200, {"teams": []})

            with patch.object(client.session, "get", return_value=mock_response):
                with pytest.raises(NotFoundError):
                    client.get_team_id_by_name("Nonexistent Team")

    def test_get_team_id_timeout(self, mock_cache_path):
        """Test TimeoutError when request times out."""
        import requests

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with patch.object(
                client.session,
                "get",
                side_effect=requests.exceptions.Timeout("Request timed out"),
            ):
                with pytest.raises(TimeoutError):
                    client.get_team_id_by_name("Manchester United")

    def test_get_team_id_connection_error(self, mock_cache_path):
        """Test ConnectionError on network error."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with patch.object(
                client.session,
                "get",
                side_effect=Exception("Network error"),
            ):
                with pytest.raises(ConnectionError):
                    client.get_team_id_by_name("Manchester United")


class TestFDClientFetchFixtures:
    """Tests for FDClient fetch_fixtures method."""

    def test_fetch_fixtures_success(
        self, mock_cache_path, mock_api_response, sample_match_data
    ):
        """Test successful fixture fetching."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            # Mock get_team_id_by_name
            with patch.object(client, "get_team_id_by_name", return_value=66):
                # Mock API response for fixtures
                mock_response = mock_api_response(200, {"matches": [sample_match_data]})

                with patch.object(client.session, "get", return_value=mock_response):
                    result = client.fetch_fixtures("Manchester United")

                assert len(result) == 1
                assert result[0].home_team == "Man United"
                assert result[0].away_team == "Liverpool"

    def test_fetch_fixtures_with_competitions_filter(
        self, mock_cache_path, mock_api_response, sample_match_data
    ):
        """Test fixture fetching with competition filter."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with patch.object(client, "get_team_id_by_name", return_value=66):
                match_2 = {
                    "id": "2",
                    "status": "SCHEDULED",
                    "utcDate": "2025-11-20T20:00:00Z",
                    "homeTeam": {
                        "name": "Arsenal",
                        "shortName": "Arsenal",
                        "id": 1,
                    },
                    "awayTeam": {
                        "name": "Manchester United",
                        "shortName": "Man United",
                        "id": 66,
                    },
                    "venue": "Emirates Stadium",
                    "competition": {
                        "code": "CL",
                        "name": "Champions League",
                    },
                    "matchday": 2,
                }

                mock_response = mock_api_response(
                    200, {"matches": [sample_match_data, match_2]}
                )

                with patch.object(client.session, "get", return_value=mock_response):
                    result = client.fetch_fixtures(
                        "Manchester United", competitions=["PL"]
                    )

                assert len(result) == 1
                assert result[0].competition_code == "PL"

    def test_fetch_fixtures_timeout(self, mock_cache_path):
        """Test TimeoutError on fixture fetching."""
        import requests

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with patch.object(client, "get_team_id_by_name", return_value=66):
                with patch.object(
                    client.session,
                    "get",
                    side_effect=requests.exceptions.Timeout("Request timed out"),
                ):
                    with pytest.raises(TimeoutError):
                        client.fetch_fixtures("Manchester United")

    def test_fetch_fixtures_connection_error(self, mock_cache_path):
        """Test ConnectionError on fixture fetching."""
        import requests

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with patch.object(client, "get_team_id_by_name", return_value=66):
                with patch.object(
                    client.session,
                    "get",
                    side_effect=requests.exceptions.ConnectionError("Network error"),
                ):
                    with pytest.raises(ConnectionError):
                        client.fetch_fixtures("Manchester United")

    def test_fetch_fixtures_with_season_filter(
        self, mock_cache_path, mock_api_response, sample_match_data
    ):
        """Test fixture fetching with season filter."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with patch.object(client, "get_team_id_by_name", return_value=66):
                mock_response = mock_api_response(200, {"matches": [sample_match_data]})

                with patch.object(
                    client.session, "get", return_value=mock_response
                ) as mock_get:
                    result = client.fetch_fixtures("Manchester United", season=2025)

                assert len(result) == 1
                # Verify that season parameter was passed to API call
                call_kwargs = mock_get.call_args.kwargs
                assert call_kwargs["params"]["season"] == 2025

    def test_fetch_fixtures_missing_utc_date(
        self, mock_cache_path, mock_api_response, sample_match_data
    ):
        """Test fixture fetching when utcDate is missing."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with patch.object(client, "get_team_id_by_name", return_value=66):
                # Remove utcDate from sample data
                match_data = {**sample_match_data}
                del match_data["utcDate"]
                mock_response = mock_api_response(200, {"matches": [match_data]})

                with patch.object(client.session, "get", return_value=mock_response):
                    result = client.fetch_fixtures("Manchester United")

                assert len(result) == 1
                assert result[0].utc_kickoff is None

    def test_fetch_fixtures_invalid_utc_date(
        self, mock_cache_path, mock_api_response, sample_match_data
    ):
        """Test fixture fetching when utcDate has invalid format."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with patch.object(client, "get_team_id_by_name", return_value=66):
                # Create match with invalid date
                match_data = {**sample_match_data, "utcDate": "invalid-date"}
                mock_response = mock_api_response(200, {"matches": [match_data]})

                with patch.object(client.session, "get", return_value=mock_response):
                    result = client.fetch_fixtures("Manchester United")

                assert len(result) == 1
                assert result[0].utc_kickoff is None

    def test_fetch_fixtures_empty_matches(self, mock_cache_path, mock_api_response):
        """Test fixture fetching when no matches are returned."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with patch.object(client, "get_team_id_by_name", return_value=66):
                mock_response = mock_api_response(200, {"matches": []})

                with patch.object(client.session, "get", return_value=mock_response):
                    result = client.fetch_fixtures("Manchester United")

                assert len(result) == 0


class TestFDClientSaveCacheErrors:
    """Tests for _save_cache error handling."""

    def test_save_cache_with_yaml_error(self, mock_cache_path):
        """Test that YAML errors in _save_cache are handled."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            client.cache = {
                "Premier League": {"Manchester United": {"id": 66, "short_name": "MUN"}}
            }

            # Mock yaml.safe_dump to raise YAMLError
            with patch(
                "backend.api.football_data.yaml.safe_dump",
                side_effect=yaml.YAMLError("YAML error"),
            ):
                # Should not raise, just log error
                client._save_cache()

    def test_save_cache_cache_path_is_directory(self, tmp_path):
        """Test _save_cache when cache_path is a directory."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        with patch("backend.api.football_data.CACHE_PATH", cache_dir):
            with patch(
                "backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"
            ):
                client = FDClient()
                client.cache = {
                    "Premier League": {
                        "Manchester United": {"id": 66, "short_name": "MUN"}
                    }
                }

                client._save_cache()
                # Should return early and not save

    @pytest.mark.parametrize(
        "invalid_cache",
        [
            "invalid",  # Not a dict
            {"Premier League": "invalid"},  # League is not a dict
        ],
    )
    def test_save_cache_invalid_structure(self, mock_cache_path, invalid_cache):
        """Test _save_cache with various invalid structures."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            client.cache = invalid_cache

            client._save_cache()
            # Should return early and not save


class TestFDClientLoadCacheErrors:
    """Tests for _load_cache error handling."""

    def test_load_cache_yaml_error(self, tmp_path):
        """Test loading cache when YAML is invalid."""
        cache_file = tmp_path / "teams.yaml"
        cache_file.write_text("invalid: yaml: content: [")

        with patch("backend.api.football_data.CACHE_PATH", cache_file):
            with patch(
                "backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"
            ):
                client = FDClient()
                assert client.cache == {}

    def test_load_cache_with_non_dict_leagues(self, tmp_path):
        """Test loading cache where some leagues have non-dict values."""
        cache_file = tmp_path / "teams.yaml"
        cache_data = {
            "Premier League": {"Manchester United": {"id": 66, "short_name": "MUN"}},
            "Championship": "invalid",
        }
        cache_file.write_text(yaml.safe_dump(cache_data))

        with patch("backend.api.football_data.CACHE_PATH", cache_file):
            with patch(
                "backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"
            ):
                client = FDClient()
                # Should load what it can
                assert "Premier League" in client.cache


class TestFDClientRefreshCacheErrors:
    """Tests for refresh_team_cache error handling."""

    def test_refresh_team_cache_api_error(self, mock_cache_path, mock_api_response):
        """Test refresh_team_cache when API returns error."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            mock_response = mock_api_response(500)

            with patch.object(client.session, "get", return_value=mock_response):
                with pytest.raises(ConnectionError):
                    client.refresh_team_cache(competitions=["PL"])

    def test_refresh_team_cache_no_teams_in_response(
        self, mock_cache_path, mock_api_response
    ):
        """Test refresh_team_cache when response contains no teams."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            mock_response = mock_api_response(200, {"teams": []})

            with patch.object(client.session, "get", return_value=mock_response):
                client.refresh_team_cache(competitions=["PL"])
                # Should complete without error but log warning

    def test_refresh_team_cache_custom_cache_path(self, tmp_path, mock_api_response):
        """Test refresh_team_cache with custom cache path."""
        custom_cache_path = tmp_path / "custom_teams.yaml"

        with patch("backend.api.football_data.CACHE_PATH", tmp_path / "teams.yaml"):
            with patch(
                "backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"
            ):
                client = FDClient()
                mock_response = mock_api_response(
                    200, {"teams": [{"name": "Team A", "id": 1, "shortName": "TA"}]}
                )

                with patch.object(client.session, "get", return_value=mock_response):
                    client.refresh_team_cache(
                        competitions=["PL"], cache_path=custom_cache_path
                    )

                # Verify cache_path was updated
                assert client.cache_path == custom_cache_path

    def test_refresh_team_cache_success_with_teams(
        self, mock_cache_path, mock_api_response
    ):
        """Test successful team cache refresh with multiple teams."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            mock_response = mock_api_response(
                200,
                {
                    "teams": [
                        {"name": "Team A", "id": 1, "shortName": "TA"},
                        {"name": "Team B", "id": 2, "shortName": "TB"},
                    ]
                },
            )

            with patch.object(client.session, "get", return_value=mock_response):
                client.refresh_team_cache(competitions=["PL"])

            assert "Team A" in client.cache["Premier League"]
            assert client.cache["Premier League"]["Team A"]["id"] == 1
            assert mock_cache_path.exists()


class TestFDClientGetTeamIdErrors:
    """Tests for get_team_id_by_name error scenarios."""

    def test_get_team_id_no_teams_in_api_response(
        self, mock_cache_path, mock_api_response
    ):
        """Test get_team_id when API returns empty teams list."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            mock_response = mock_api_response(200, {})

            with patch.object(client.session, "get", return_value=mock_response):
                with pytest.raises(NotFoundError):
                    client.get_team_id_by_name("Manchester United")

    def test_get_team_id_by_short_name_from_api(
        self, mock_cache_path, mock_api_response
    ):
        """Test getting team ID by short name from API."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            mock_response = mock_api_response(
                200,
                {
                    "teams": [
                        {"name": "Manchester United", "shortName": "Man Utd", "id": 66},
                    ]
                },
            )

            with patch.object(client.session, "get", return_value=mock_response):
                result = client.get_team_id_by_name("Man Utd")

            assert result == 66


class TestFDClientAddToCache:
    """Tests for _add_to_cache functionality."""

    def test_add_to_cache_with_venue(self, mock_cache_path):
        """Test adding team to cache with venue information."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            client._add_to_cache(
                "Premier League",
                "manchester united",
                66,
                "Man Utd",
                "Old Trafford",
            )

            assert client.cache["Premier League"]["Manchester United"]["id"] == 66
            assert (
                client.cache["Premier League"]["Manchester United"]["venue"]
                == "Old Trafford"
            )


class TestFootballDataRepository:
    """Tests for FootballDataRepository class."""

    def test_repository_with_custom_client(self, mock_cache_path):
        """Test FootballDataRepository with a custom client."""
        from backend.api.football_data import FootballDataRepository

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            custom_client = FDClient()
            repo = FootballDataRepository(client=custom_client)
            assert repo.client == custom_client

    def test_repository_creates_default_client(self, mock_cache_path):
        """Test FootballDataRepository creates a default client."""
        from backend.api.football_data import FootballDataRepository

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            repo = FootballDataRepository()
            assert repo.client is not None
            assert isinstance(repo.client, FDClient)

    def test_repository_fetch_fixtures(self, mock_cache_path):
        """Test FootballDataRepository.fetch_fixtures delegates to client."""
        from backend.api.football_data import FootballDataRepository

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            repo = FootballDataRepository()

            with patch.object(
                repo.client, "fetch_fixtures", return_value=[]
            ) as mock_fetch:
                repo.fetch_fixtures(
                    "Manchester United", competitions=["PL"], season=2025
                )

                mock_fetch.assert_called_once_with("Manchester United", ["PL"], 2025)


class TestFDClientFetchFixturesAdditional:
    """Additional tests for fetch_fixtures."""

    def test_fetch_fixtures_away_match(
        self, mock_cache_path, mock_api_response, sample_match_data
    ):
        """Test fetch_fixtures correctly identifies away matches."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with patch.object(client, "get_team_id_by_name", return_value=66):
                # Swap home and away teams for away match
                away_match = {**sample_match_data}
                away_match["homeTeam"] = {
                    "name": "Liverpool",
                    "shortName": "Liverpool",
                    "id": 64,
                }
                away_match["awayTeam"] = {
                    "name": "Manchester United",
                    "shortName": "Man United",
                    "id": 66,
                }
                away_match["venue"] = "Anfield"

                mock_response = mock_api_response(200, {"matches": [away_match]})

                with patch.object(client.session, "get", return_value=mock_response):
                    result = client.fetch_fixtures("Manchester United")

                assert len(result) == 1
                assert result[0].is_home is False

    def test_fetch_fixtures_filters_by_competition(
        self, mock_cache_path, mock_api_response, sample_match_data
    ):
        """Test fetch_fixtures correctly filters by competition."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with patch.object(client, "get_team_id_by_name", return_value=66):
                match_2 = {
                    "id": "2",
                    "status": "SCHEDULED",
                    "utcDate": "2025-11-20T20:00:00Z",
                    "homeTeam": {
                        "name": "Arsenal",
                        "shortName": "Arsenal",
                        "id": 1,
                    },
                    "awayTeam": {
                        "name": "Manchester United",
                        "shortName": "Man United",
                        "id": 66,
                    },
                    "venue": "Emirates",
                    "competition": {"code": "CL", "name": "Champions League"},
                    "matchday": 2,
                }

                mock_response = mock_api_response(
                    200, {"matches": [sample_match_data, match_2]}
                )

                with patch.object(client.session, "get", return_value=mock_response):
                    result = client.fetch_fixtures(
                        "Manchester United", competitions=["PL"]
                    )

                assert len(result) == 1
                assert result[0].competition_code == "PL"

    def test_fetch_fixtures_with_venue_from_cache(
        self, tmp_path, mock_api_response, sample_match_data
    ):
        """Test fetch_fixtures includes venue information from cache."""
        cache_file = tmp_path / "teams.yaml"
        cache_data = {
            "Premier League": {
                "Manchester United": {
                    "id": 66,
                    "short_name": "Man Utd",
                    "venue": "Old Trafford",
                }
            }
        }
        cache_file.write_text(yaml.safe_dump(cache_data))

        with patch("backend.api.football_data.CACHE_PATH", cache_file):
            with patch(
                "backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"
            ):
                client = FDClient()

                with patch.object(client, "get_team_id_by_name", return_value=66):
                    # Remove venue from API response so it comes from cache
                    match_data = {**sample_match_data}
                    del match_data["venue"]
                    mock_response = mock_api_response(200, {"matches": [match_data]})

                    with patch.object(
                        client.session, "get", return_value=mock_response
                    ):
                        result = client.fetch_fixtures("Manchester United")

                    assert result[0].venue == "Old Trafford"
