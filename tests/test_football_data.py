"""Tests for Football Data API client."""

from unittest.mock import Mock, patch

import pytest
import yaml

from src.backend.api.football_data import COMP_CODES, FDClient
from src.utils.errors import (
    AuthenticationError,
    ConnectionError,
    NotFoundError,
    ParsingError,
    RateLimitError,
    ServerError,
    TimeoutError,
)


class TestFDClientInitialisation:
    """Tests for FDClient initialisation."""

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_client_initialisation_success(self):
        """Test successful client initialisation."""
        client = FDClient()
        assert client.token == {"X-Auth-Token": "test_token"}
        assert client.session is not None

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", None)
    def test_client_initialisation_no_token(self):
        """Test that initialisation fails without token."""
        with pytest.raises(AuthenticationError):
            FDClient()


class TestFDClientCache:
    """Tests for FDClient cache operations."""

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_load_cache_success(self, tmp_path):
        """Test loading cache from file."""
        cache_file = tmp_path / "teams.yaml"
        cache_data = {
            "Premier League": {
                "Manchester United": {"id": 66, "short_name": "Man Utd"},
                "Liverpool": {"id": 64, "short_name": "Liverpool"},
            }
        }
        cache_file.write_text(yaml.safe_dump(cache_data))

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()
            assert client.cache == cache_data

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_load_cache_file_not_exists(self, tmp_path):
        """Test loading cache when file doesn't exist."""
        cache_file = tmp_path / "nonexistent.yaml"

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()
            assert client.cache == {}

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_save_cache(self, tmp_path):
        """Test saving cache to file."""
        cache_file = tmp_path / "teams.yaml"

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()
            client.cache = {
                "Premier League": {
                    "Team A": {"id": 1, "short_name": "TAM"},
                    "Team B": {"id": 2, "short_name": "TMB"},
                }
            }
            client._save_cache()

            assert cache_file.exists()
            loaded_data = yaml.safe_load(cache_file.read_text())
            assert loaded_data == {
                "Premier League": {
                    "Team A": {"id": 1, "short_name": "TAM"},
                    "Team B": {"id": 2, "short_name": "TMB"},
                }
            }

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_add_to_cache(self, tmp_path):
        """Test adding team to cache."""
        cache_file = tmp_path / "teams.yaml"

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()
            client._add_to_cache("Premier League", "Chelsea", 61, "CHE")

            assert client.cache["Premier League"]["Chelsea"]["id"] == 61
            assert client.cache["Premier League"]["Chelsea"]["short_name"] == "CHE"
            assert cache_file.exists()


class TestFDClientHandleResponse:
    """Tests for FDClient response handling."""

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_success(self):
        """Test handling successful response."""
        client = FDClient()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "value"}

        result = client._handle_response(mock_response, "test context")
        assert result == {"data": "value"}

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_404(self):
        """Test handling 404 response."""
        client = FDClient()
        mock_response = Mock()
        mock_response.status_code = 404

        with pytest.raises(NotFoundError):
            client._handle_response(mock_response, "test context")

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_429(self):
        """Test handling rate limit response."""
        client = FDClient()
        mock_response = Mock()
        mock_response.status_code = 429

        with pytest.raises(RateLimitError):
            client._handle_response(mock_response, "test context")

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_500(self):
        """Test handling server error response."""
        client = FDClient()
        mock_response = Mock()
        mock_response.status_code = 500

        with pytest.raises(ServerError):
            client._handle_response(mock_response, "test context")

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_invalid_json(self):
        """Test handling response with invalid JSON."""
        client = FDClient()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with pytest.raises(ParsingError):
            client._handle_response(mock_response, "test context")

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_non_dict_json(self):
        """Test handling response with non-dict JSON."""
        client = FDClient()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["not", "a", "dict"]

        with pytest.raises(ParsingError):
            client._handle_response(mock_response, "test context")


class TestFDClientRefreshCache:
    """Tests for FDClient cache refresh."""

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_refresh_team_cache_success(self, tmp_path):
        """Test successful team cache refresh."""
        cache_file = tmp_path / "teams.yaml"

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "teams": [
                    {"name": "Team A", "id": 1, "shortName": "TA"},
                    {"name": "Team B", "id": 2, "shortName": "TB"},
                ]
            }

            with patch.object(client.session, "get", return_value=mock_response):
                client.refresh_team_cache(competitions=["PL"])

            assert "Team A" in client.cache["Premier League"]
            assert client.cache["Premier League"]["Team A"]["id"] == 1
            assert client.cache["Premier League"]["Team A"]["short_name"] == "TA"
            assert cache_file.exists()

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_refresh_team_cache_all_competitions(self, tmp_path):
        """Test refreshing cache for all competitions."""
        cache_file = tmp_path / "teams.yaml"

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"teams": []}

            with patch.object(
                client.session, "get", return_value=mock_response
            ) as mock_get:
                # Should default to all competition codes
                client.refresh_team_cache()

            # Should have made calls for all default competitions
            assert mock_get.call_count == len(COMP_CODES)


class TestFDClientGetTeamId:
    """Tests for FDClient get_team_id_by_name method."""

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_get_team_id_from_cache(self, tmp_path):
        """Test getting team ID from cache."""
        cache_file = tmp_path / "teams.yaml"
        cache_data = {
            "Premier League": {"Manchester United": {"id": 66, "short_name": "MUN"}}
        }
        cache_file.write_text(yaml.safe_dump(cache_data))

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()
            result = client.get_team_id_by_name("Manchester United")

            assert result == 66

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_get_team_id_case_insensitive_cache(self, tmp_path):
        """Test getting team ID from cache is case-insensitive."""
        cache_file = tmp_path / "teams.yaml"
        cache_data = {
            "Premier League": {"Manchester United": {"id": 66, "short_name": "MUN"}}
        }
        cache_file.write_text(yaml.safe_dump(cache_data))

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()
            result = client.get_team_id_by_name("manchester united")

            assert result == 66

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_get_team_id_from_api(self, tmp_path):
        """Test getting team ID from API when not in cache."""
        cache_file = tmp_path / "teams.yaml"

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "teams": [
                    {"name": "Manchester United", "shortName": "Man United", "id": 66},
                ]
            }

            with patch.object(client.session, "get", return_value=mock_response):
                result = client.get_team_id_by_name("Manchester United")

            assert result == 66

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_get_team_id_by_short_name(self, tmp_path):
        """Test getting team ID by short name."""
        cache_file = tmp_path / "teams.yaml"

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "teams": [
                    {"name": "Manchester United", "shortName": "Man United", "id": 66},
                ]
            }

            with patch.object(client.session, "get", return_value=mock_response):
                result = client.get_team_id_by_name("Man United")

            assert result == 66

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_get_team_id_not_found(self, tmp_path):
        """Test NotFoundError when team not found."""
        cache_file = tmp_path / "teams.yaml"

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"teams": []}

            with patch.object(client.session, "get", return_value=mock_response):
                with pytest.raises(NotFoundError):
                    client.get_team_id_by_name("Nonexistent Team")

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_get_team_id_timeout(self, tmp_path):
        """Test TimeoutError when request times out."""
        import requests

        cache_file = tmp_path / "teams.yaml"

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()

            with patch.object(
                client.session,
                "get",
                side_effect=requests.exceptions.Timeout("Request timed out"),
            ):
                with pytest.raises(TimeoutError):
                    client.get_team_id_by_name("Manchester United")

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_get_team_id_connection_error(self, tmp_path):
        """Test ConnectionError on network error."""
        cache_file = tmp_path / "teams.yaml"

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
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

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_fetch_fixtures_success(self, tmp_path):
        """Test successful fixture fetching."""
        cache_file = tmp_path / "teams.yaml"

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()

            # Mock get_team_id_by_name
            with patch.object(client, "get_team_id_by_name", return_value=66):
                # Mock API response for fixtures
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "matches": [
                        {
                            "id": "1",
                            "status": "SCHEDULED",
                            "utcDate": "2025-11-15T15:00:00Z",
                            "homeTeam": {
                                "name": "Manchester United",
                                "shortName": "Man United",
                                "id": 66,
                            },
                            "awayTeam": {
                                "name": "Liverpool",
                                "shortName": "Liverpool",
                                "id": 64,
                            },
                            "venue": "Old Trafford",
                            "competition": {
                                "code": "PL",
                                "name": "Premier League",
                            },
                            "matchday": 10,
                        }
                    ]
                }

                with patch.object(client.session, "get", return_value=mock_response):
                    result = client.fetch_fixtures("Manchester United")

                assert len(result) == 1
                assert result[0].home_team == "Man United"
                assert result[0].away_team == "Liverpool"

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_fetch_fixtures_with_competitions_filter(self, tmp_path):
        """Test fixture fetching with competition filter."""
        cache_file = tmp_path / "teams.yaml"

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()

            with patch.object(client, "get_team_id_by_name", return_value=66):
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "matches": [
                        {
                            "id": "1",
                            "status": "SCHEDULED",
                            "utcDate": "2025-11-15T15:00:00Z",
                            "homeTeam": {
                                "name": "Manchester United",
                                "shortName": "Man United",
                                "id": 66,
                            },
                            "awayTeam": {
                                "name": "Liverpool",
                                "shortName": "Liverpool",
                                "id": 64,
                            },
                            "venue": "Old Trafford",
                            "competition": {
                                "code": "PL",
                                "name": "Premier League",
                            },
                            "matchday": 10,
                        },
                        {
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
                        },
                    ]
                }

                with patch.object(client.session, "get", return_value=mock_response):
                    result = client.fetch_fixtures(
                        "Manchester United", competitions=["PL"]
                    )

                assert len(result) == 1
                assert result[0].competition_code == "PL"

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_fetch_fixtures_timeout(self, tmp_path):
        """Test TimeoutError on fixture fetching."""
        import requests

        cache_file = tmp_path / "teams.yaml"

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()

            with patch.object(client, "get_team_id_by_name", return_value=66):
                with patch.object(
                    client.session,
                    "get",
                    side_effect=requests.exceptions.Timeout("Request timed out"),
                ):
                    with pytest.raises(TimeoutError):
                        client.fetch_fixtures("Manchester United")

    @patch("src.backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_fetch_fixtures_connection_error(self, tmp_path):
        """Test ConnectionError on fixture fetching."""
        import requests

        cache_file = tmp_path / "teams.yaml"

        with patch("src.backend.api.football_data.CACHE_PATH", cache_file):
            client = FDClient()

            with patch.object(client, "get_team_id_by_name", return_value=66):
                with patch.object(
                    client.session,
                    "get",
                    side_effect=requests.exceptions.ConnectionError("Network error"),
                ):
                    with pytest.raises(ConnectionError):
                        client.fetch_fixtures("Manchester United")
