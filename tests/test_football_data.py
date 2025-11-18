"""Tests for Football Data API client."""

from unittest.mock import Mock, patch

import pytest
import yaml

from src.providers.football_data import COMP_CODES, FDClient
from src.utils.errors import (
    AuthenticationError,
    NotFoundError,
    ParsingError,
    RateLimitError,
    ServerError,
)


class TestFDClientInitialization:
    """Tests for FDClient initialization."""

    @patch("src.providers.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_client_initialization_success(self):
        """Test successful client initialization."""
        client = FDClient()
        assert client.token == {"X-Auth-Token": "test_token"}
        assert client.session is not None

    @patch("src.providers.football_data.FOOTBALL_DATA_API_TOKEN", None)
    def test_client_initialization_no_token(self):
        """Test that initialization fails without token."""
        with pytest.raises(AuthenticationError):
            FDClient()


class TestFDClientCache:
    """Tests for FDClient cache operations."""

    @patch("src.providers.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_load_cache_success(self, tmp_path):
        """Test loading cache from file."""
        cache_file = tmp_path / "teams.yaml"
        cache_data = {"Manchester United": 66, "Liverpool": 64}
        cache_file.write_text(yaml.safe_dump(cache_data))

        with patch("src.providers.football_data.CACHE_PATH", cache_file):
            client = FDClient()
            assert client.cache == cache_data

    @patch("src.providers.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_load_cache_file_not_exists(self, tmp_path):
        """Test loading cache when file doesn't exist."""
        cache_file = tmp_path / "nonexistent.yaml"

        with patch("src.providers.football_data.CACHE_PATH", cache_file):
            client = FDClient()
            assert client.cache == {}

    @patch("src.providers.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_save_cache(self, tmp_path):
        """Test saving cache to file."""
        cache_file = tmp_path / "teams.yaml"

        with patch("src.providers.football_data.CACHE_PATH", cache_file):
            client = FDClient()
            client.cache = {"Team A": 1, "Team B": 2}
            client._save_cache()

            assert cache_file.exists()
            loaded_data = yaml.safe_load(cache_file.read_text())
            assert loaded_data == {"Team A": 1, "Team B": 2}

    @patch("src.providers.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_add_to_cache(self, tmp_path):
        """Test adding team to cache."""
        cache_file = tmp_path / "teams.yaml"

        with patch("src.providers.football_data.CACHE_PATH", cache_file):
            client = FDClient()
            client._add_to_cache("Chelsea", 61)

            assert client.cache["Chelsea"] == 61
            assert cache_file.exists()


class TestFDClientHandleResponse:
    """Tests for FDClient response handling."""

    @patch("src.providers.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_success(self):
        """Test handling successful response."""
        client = FDClient()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "value"}

        result = client._handle_response(mock_response, "test context")
        assert result == {"data": "value"}

    @patch("src.providers.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_404(self):
        """Test handling 404 response."""
        client = FDClient()
        mock_response = Mock()
        mock_response.status_code = 404

        with pytest.raises(NotFoundError):
            client._handle_response(mock_response, "test context")

    @patch("src.providers.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_429(self):
        """Test handling rate limit response."""
        client = FDClient()
        mock_response = Mock()
        mock_response.status_code = 429

        with pytest.raises(RateLimitError):
            client._handle_response(mock_response, "test context")

    @patch("src.providers.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_500(self):
        """Test handling server error response."""
        client = FDClient()
        mock_response = Mock()
        mock_response.status_code = 500

        with pytest.raises(ServerError):
            client._handle_response(mock_response, "test context")

    @patch("src.providers.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_handle_response_invalid_json(self):
        """Test handling response with invalid JSON."""
        client = FDClient()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with pytest.raises(ParsingError):
            client._handle_response(mock_response, "test context")

    @patch("src.providers.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
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

    @patch("src.providers.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_refresh_team_cache_success(self, tmp_path):
        """Test successful team cache refresh."""
        cache_file = tmp_path / "teams.yaml"

        with patch("src.providers.football_data.CACHE_PATH", cache_file):
            client = FDClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "teams": [
                    {"name": "Team A", "id": 1},
                    {"name": "Team B", "id": 2},
                ]
            }

            with patch.object(client.session, "get", return_value=mock_response):
                client.refresh_team_cache(competitions=["PL"])

            assert "Team A" in client.cache
            assert client.cache["Team A"] == 1
            assert cache_file.exists()

    @patch("src.providers.football_data.FOOTBALL_DATA_API_TOKEN", "test_token")
    def test_refresh_team_cache_all_competitions(self, tmp_path):
        """Test refreshing cache for all competitions."""
        cache_file = tmp_path / "teams.yaml"

        with patch("src.providers.football_data.CACHE_PATH", cache_file):
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
