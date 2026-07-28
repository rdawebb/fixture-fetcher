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

    def test_load_cache_file_not_exists(self):
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

    def test_refresh_team_cache_merges_other_leagues(self, mock_api_response):
        """Test refreshing one competition leaves other cached leagues intact."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            client.cache = {
                "Championship": {
                    "Team C": {"id": 3, "short_name": "TC"},
                }
            }

            mock_response = mock_api_response(
                200, {"teams": [{"name": "Team A", "id": 1, "shortName": "TA"}]}
            )

            with patch.object(client.session, "get", return_value=mock_response):
                client.refresh_team_cache(competitions=["PL"])

            assert client.cache["Championship"]["Team C"]["id"] == 3
            assert client.cache["Premier League"]["Team A"]["id"] == 1

    def test_refresh_team_cache_stores_team_metadata(self, mock_api_response):
        """Test venue, colours and crest are kept from the teams response."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            mock_response = mock_api_response(
                200,
                {
                    "teams": [
                        {
                            "name": "Manchester United",
                            "id": 66,
                            "shortName": "Man Utd",
                            "venue": "Old Trafford",
                            "clubColors": "Red / White",
                            "crest": "https://example.com/66.png",
                        }
                    ]
                },
            )

            with patch.object(client.session, "get", return_value=mock_response):
                client.refresh_team_cache(competitions=["PL"])

            cached = client.cache["Premier League"]["Manchester United"]
            assert cached["venue"] == "Old Trafford"
            assert cached["club_colors"] == "Red / White"
            assert cached["crest"] == "https://example.com/66.png"

    def test_refresh_team_cache_all_competitions(self, mock_api_response):
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

    def test_get_team_id_from_match_data(
        self, mock_api_response, competition_matches_response
    ):
        """Test resolving a cache miss from the competition match payload."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            mock_response = mock_api_response(200, competition_matches_response())

            with patch.object(
                client.session, "get", return_value=mock_response
            ) as mock_get:
                result = client.get_team_id_by_name("Manchester United")

            assert result == 66
            # Resolved from the matches endpoint, not a bespoke /teams request
            assert "competitions/PL/matches" in mock_get.call_args.args[0]

    def test_get_team_id_from_match_data_caches_team(
        self, mock_api_response, competition_matches_response
    ):
        """Test a team resolved from match data is written to the cache."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            mock_response = mock_api_response(200, competition_matches_response())

            with patch.object(client.session, "get", return_value=mock_response):
                client.get_team_id_by_name("Manchester United")

            cached = client.cache["Premier League"]["Manchester United"]
            assert cached["id"] == 66
            assert cached["short_name"] == "Man United"

    def test_get_team_id_by_short_name_from_match_data(
        self, mock_api_response, competition_matches_response
    ):
        """Test resolving a team by its short name from match data."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            mock_response = mock_api_response(200, competition_matches_response())

            with patch.object(client.session, "get", return_value=mock_response):
                result = client.get_team_id_by_name("Man United")

            assert result == 66

    def test_get_team_id_searches_all_competitions(
        self, mock_api_response, competition_matches_response
    ):
        """Test a miss in one competition falls through to the next."""
        elc_match = {
            "id": "9",
            "status": "SCHEDULED",
            "utcDate": "2025-11-15T15:00:00Z",
            "homeTeam": {"name": "Leeds United", "shortName": "Leeds", "id": 341},
            "awayTeam": {"name": "Norwich City", "shortName": "Norwich", "id": 68},
            "competition": {"code": "ELC", "name": "Championship"},
            "matchday": 10,
        }

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            responses = [
                mock_api_response(200, competition_matches_response(matches=[])),
                mock_api_response(
                    200,
                    competition_matches_response(
                        matches=[elc_match], code="ELC", name="Championship"
                    ),
                ),
            ]

            with patch.object(client.session, "get", side_effect=responses):
                result = client.get_team_id_by_name("Leeds United", ["PL", "ELC"])

            assert result == 341
            assert client.cache["ELC"]["Leeds United"]["id"] == 341

    def test_get_team_id_not_found(
        self, mock_api_response, competition_matches_response
    ):
        """Test NotFoundError when team not found."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            mock_response = mock_api_response(
                200, competition_matches_response(matches=[])
            )

            with (
                patch.object(client.session, "get", return_value=mock_response),
                pytest.raises(NotFoundError),
            ):
                client.get_team_id_by_name("Nonexistent Team")

    def test_get_team_id_timeout(self):
        """Test TimeoutError when request times out."""
        import requests

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with (
                patch.object(
                    client.session,
                    "get",
                    side_effect=requests.exceptions.Timeout("Request timed out"),
                ),
                pytest.raises(TimeoutError),
            ):
                client.get_team_id_by_name("Manchester United")

    def test_get_team_id_connection_error(self):
        """Test ConnectionError on network error."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with (
                patch.object(
                    client.session,
                    "get",
                    side_effect=Exception("Network error"),
                ),
                pytest.raises(ConnectionError),
            ):
                client.get_team_id_by_name("Manchester United")

    def test_get_team_id_requests_connection_error(self):
        """Test a requests ConnectionError surfaces, not an UnboundLocalError."""
        import requests

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with (
                patch.object(
                    client.session,
                    "get",
                    side_effect=requests.exceptions.ConnectionError("Network error"),
                ),
                pytest.raises(ConnectionError) as exc_info,
            ):
                client.get_team_id_by_name("Manchester United")

            assert "competition PL" in str(exc_info.value)


class TestFDClientFetchFixtures:
    """Tests for FDClient fetch_fixtures method."""

    def test_fetch_fixtures_success(self, mock_api_response, sample_match_data):
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
        self, mock_api_response, sample_match_data
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

    def test_fetch_fixtures_timeout(self):
        """Test TimeoutError on fixture fetching."""
        import requests

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with (
                patch.object(client, "get_team_id_by_name", return_value=66),
                patch.object(
                    client.session,
                    "get",
                    side_effect=requests.exceptions.Timeout("Request timed out"),
                ),
                pytest.raises(TimeoutError),
            ):
                client.fetch_fixtures("Manchester United")

    def test_fetch_fixtures_connection_error(self):
        """Test ConnectionError on fixture fetching."""
        import requests

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with (
                patch.object(client, "get_team_id_by_name", return_value=66),
                patch.object(
                    client.session,
                    "get",
                    side_effect=requests.exceptions.ConnectionError("Network error"),
                ),
                pytest.raises(ConnectionError),
            ):
                client.fetch_fixtures("Manchester United")

    def test_fetch_fixtures_with_season_filter(
        self, mock_api_response, sample_match_data
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
        self, mock_api_response, sample_match_data
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
        self, mock_api_response, sample_match_data
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

    def test_fetch_fixtures_empty_matches(self, mock_api_response):
        """Test fixture fetching when no matches are returned."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()

            with patch.object(client, "get_team_id_by_name", return_value=66):
                mock_response = mock_api_response(200, {"matches": []})

                with patch.object(client.session, "get", return_value=mock_response):
                    result = client.fetch_fixtures("Manchester United")

                assert len(result) == 0


class TestFDClientCompetitionMatches:
    """Tests for the single-request-per-competition fetch strategy."""

    def test_fetch_uses_competition_endpoint(
        self, cache_with_teams, mock_api_response, competition_matches_response
    ):
        """Test fixtures come from the competition endpoint, not the team endpoint."""
        client = cache_with_teams
        mock_response = mock_api_response(200, competition_matches_response())

        with patch.object(
            client.session, "get", return_value=mock_response
        ) as mock_get:
            client.fetch_fixtures("Manchester United", competitions=["PL"])

        url = mock_get.call_args.args[0]
        assert url.endswith("competitions/PL/matches")

    def test_one_request_serves_every_team(
        self, cache_with_teams, mock_api_response, competition_matches_response
    ):
        """Test a second team reuses the memoised payload instead of refetching.

        This is the whole point of the competition-wide fetch: request count must
        scale with competitions, not with teams.
        """
        client = cache_with_teams
        mock_response = mock_api_response(200, competition_matches_response())

        with patch.object(
            client.session, "get", return_value=mock_response
        ) as mock_get:
            first = client.fetch_fixtures("Manchester United", competitions=["PL"])
            second = client.fetch_fixtures("Liverpool", competitions=["PL"])

        assert mock_get.call_count == 1
        assert len(first) == 1
        assert len(second) == 1
        assert first[0].is_home is True
        assert second[0].is_home is False

    def test_memo_is_keyed_by_season(
        self, cache_with_teams, mock_api_response, competition_matches_response
    ):
        """Test different seasons are fetched separately."""
        client = cache_with_teams
        mock_response = mock_api_response(200, competition_matches_response())

        with patch.object(
            client.session, "get", return_value=mock_response
        ) as mock_get:
            client.fetch_fixtures("Manchester United", ["PL"], season=2025)
            client.fetch_fixtures("Manchester United", ["PL"], season=2026)
            client.fetch_fixtures("Manchester United", ["PL"], season=2025)

        assert mock_get.call_count == 2

    def test_failures_are_not_memoised(
        self, cache_with_teams, mock_api_response, competition_matches_response
    ):
        """Test a rate-limited competition is retried rather than cached as failed."""
        client = cache_with_teams

        responses = [
            mock_api_response(429),
            mock_api_response(200, competition_matches_response()),
        ]

        with patch.object(client.session, "get", side_effect=responses):
            with pytest.raises(RateLimitError):
                client.fetch_fixtures("Manchester United", competitions=["PL"])

            result = client.fetch_fixtures("Manchester United", competitions=["PL"])

        assert len(result) == 1

    def test_fetch_fixtures_across_multiple_competitions(
        self, cache_with_teams, mock_api_response, competition_matches_response
    ):
        """Test one request per competition, with results combined."""
        client = cache_with_teams
        cl_match = {
            "id": "3",
            "status": "SCHEDULED",
            "utcDate": "2025-12-02T20:00:00Z",
            "homeTeam": {
                "name": "Manchester United",
                "shortName": "Man United",
                "id": 66,
            },
            "awayTeam": {"name": "Real Madrid", "shortName": "Real Madrid", "id": 86},
            "competition": {"code": "CL", "name": "UEFA Champions League"},
            "matchday": 4,
        }

        responses = [
            mock_api_response(200, competition_matches_response()),
            mock_api_response(
                200,
                competition_matches_response(
                    matches=[cl_match], code="CL", name="UEFA Champions League"
                ),
            ),
        ]

        with patch.object(client.session, "get", side_effect=responses) as mock_get:
            result = client.fetch_fixtures("Manchester United", ["PL", "CL"])

        assert mock_get.call_count == 2
        assert {f.competition_code for f in result} == {"PL", "CL"}

    def test_is_home_matched_by_id_not_name(
        self, cache_with_teams, mock_api_response, competition_matches_response
    ):
        """Test home/away is decided by team ID, so caller spelling doesn't matter."""
        client = cache_with_teams
        mock_response = mock_api_response(200, competition_matches_response())

        with patch.object(client.session, "get", return_value=mock_response):
            # Cached as "Manchester United"/"MUN"; the API short name is "Man United"
            result = client.fetch_fixtures("MUN", competitions=["PL"])

        assert len(result) == 1
        assert result[0].is_home is True

    def test_competition_metadata_falls_back_to_payload_root(
        self, cache_with_teams, mock_api_response
    ):
        """Test matches without a competition block use the root competition."""
        client = cache_with_teams
        match = {
            "id": "1",
            "status": "SCHEDULED",
            "utcDate": "2025-11-15T15:00:00Z",
            "homeTeam": {
                "name": "Manchester United",
                "shortName": "Man United",
                "id": 66,
            },
            "awayTeam": {"name": "Liverpool", "shortName": "Liverpool", "id": 64},
        }
        mock_response = mock_api_response(
            200,
            {
                "competition": {"code": "PL", "name": "Premier League"},
                "matches": [match],
            },
        )

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.fetch_fixtures("Manchester United", competitions=["PL"])

        assert result[0].competition == "Premier League"
        assert result[0].competition_code == "PL"

    def test_missing_short_name_falls_back_to_full_name(
        self, cache_with_teams, mock_api_response, competition_matches_response
    ):
        """Test a null shortName in the payload doesn't produce an empty team name."""
        client = cache_with_teams
        match = {
            "id": "1",
            "status": "SCHEDULED",
            "utcDate": "2025-11-15T15:00:00Z",
            "homeTeam": {"name": "Manchester United", "shortName": None, "id": 66},
            "awayTeam": {"name": "Liverpool FC", "shortName": None, "id": 64},
            "competition": {"code": "PL", "name": "Premier League"},
        }
        mock_response = mock_api_response(
            200, competition_matches_response(matches=[match])
        )

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.fetch_fixtures("Manchester United", competitions=["PL"])

        assert result[0].home_team == "Manchester United"
        assert result[0].away_team == "Liverpool FC"

    def test_other_teams_matches_are_filtered_out(
        self, cache_with_teams, mock_api_response, competition_matches_response
    ):
        """Test only the requested team's matches survive the filter."""
        client = cache_with_teams
        other_match = {
            "id": "4",
            "status": "SCHEDULED",
            "utcDate": "2025-11-16T14:00:00Z",
            "homeTeam": {"name": "Arsenal", "shortName": "Arsenal", "id": 57},
            "awayTeam": {"name": "Chelsea", "shortName": "Chelsea", "id": 61},
            "competition": {"code": "PL", "name": "Premier League"},
        }
        mock_response = mock_api_response(
            200, competition_matches_response(matches=None)
        )
        mock_response.json.return_value["matches"].append(other_match)

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.fetch_fixtures("Manchester United", competitions=["PL"])

        assert len(result) == 1
        assert result[0].id == "1"


class TestFDClientTeamIndex:
    """Tests for the team cache index."""

    def test_index_rebuilt_after_cache_change(self, cache_with_teams):
        """Test the index picks up teams added after it was first built."""
        client = cache_with_teams
        assert "chelsea" not in client._team_index()

        client._add_to_cache("Premier League", "Chelsea", 61, "CHE")

        assert client._team_index()["chelsea"]["id"] == 61

    def test_index_skips_malformed_leagues(self, tmp_path):
        """Test a non-dict league entry doesn't break the index."""
        cache_file = tmp_path / "teams.yaml"
        cache_file.write_text(
            yaml.safe_dump(
                {
                    "Premier League": {
                        "Manchester United": {"id": 66, "short_name": "MUN"}
                    },
                    "Championship": "invalid",
                }
            )
        )

        with (
            patch("backend.api.football_data.CACHE_PATH", cache_file),
            patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"),
        ):
            client = FDClient()

        assert client._team_index()["manchester united"]["id"] == 66


class TestFDClientSaveCacheErrors:
    """Tests for _save_cache error handling."""

    def test_save_cache_with_yaml_error(self):
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

        with (
            patch("backend.api.football_data.CACHE_PATH", cache_dir),
            patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"),
        ):
            client = FDClient()
            client.cache = {
                "Premier League": {"Manchester United": {"id": 66, "short_name": "MUN"}}
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
    def test_save_cache_invalid_structure(self, invalid_cache):
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

        with (
            patch("backend.api.football_data.CACHE_PATH", cache_file),
            patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"),
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

        with (
            patch("backend.api.football_data.CACHE_PATH", cache_file),
            patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"),
        ):
            client = FDClient()
            # Should load what it can
            assert "Premier League" in client.cache


class TestFDClientRefreshCacheErrors:
    """Tests for refresh_team_cache error handling."""

    def test_refresh_team_cache_api_error(self, mock_api_response):
        """Test refresh_team_cache when API returns error."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            mock_response = mock_api_response(500)

            with (
                patch.object(client.session, "get", return_value=mock_response),
                pytest.raises(ConnectionError),
            ):
                client.refresh_team_cache(competitions=["PL"])

    def test_refresh_team_cache_no_teams_in_response(self, mock_api_response):
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

        with (
            patch("backend.api.football_data.CACHE_PATH", tmp_path / "teams.yaml"),
            patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"),
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

    def test_get_team_id_no_matches_in_api_response(self, mock_api_response):
        """Test get_team_id when the API response carries no matches."""
        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            mock_response = mock_api_response(200, {})

            with (
                patch.object(client.session, "get", return_value=mock_response),
                pytest.raises(NotFoundError),
            ):
                client.get_team_id_by_name("Manchester United")

    def test_get_team_id_by_tla_from_match_data(
        self, mock_api_response, competition_matches_response
    ):
        """Test getting team ID by three-letter abbreviation."""
        match = {
            "id": "1",
            "status": "SCHEDULED",
            "utcDate": "2025-11-15T15:00:00Z",
            "homeTeam": {
                "name": "Manchester United",
                "shortName": "Man United",
                "tla": "MUN",
                "id": 66,
            },
            "awayTeam": {"name": "Liverpool", "shortName": "Liverpool", "id": 64},
            "competition": {"code": "PL", "name": "Premier League"},
        }

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            client = FDClient()
            mock_response = mock_api_response(
                200, competition_matches_response(matches=[match])
            )

            with patch.object(client.session, "get", return_value=mock_response):
                result = client.get_team_id_by_name("MUN")

            assert result == 66


class TestFDClientAddToCache:
    """Tests for _add_to_cache functionality."""

    def test_add_to_cache_with_venue(self):
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

    def test_repository_with_custom_client(self):
        """Test FootballDataRepository with a custom client."""
        from backend.api.football_data import FootballDataRepository

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            custom_client = FDClient()
            repo = FootballDataRepository(client=custom_client)
            assert repo.client == custom_client

    def test_repository_creates_default_client(self):
        """Test FootballDataRepository creates a default client."""
        from backend.api.football_data import FootballDataRepository

        with patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"):
            repo = FootballDataRepository()
            assert repo.client is not None
            assert isinstance(repo.client, FDClient)

    def test_repository_fetch_fixtures(self):
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

    def test_fetch_fixtures_away_match(self, mock_api_response, sample_match_data):
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
        self, mock_api_response, sample_match_data
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

        with (
            patch("backend.api.football_data.CACHE_PATH", cache_file),
            patch("backend.api.football_data.FOOTBALL_DATA_API_TOKEN", "test_token"),
        ):
            client = FDClient()

            with patch.object(client, "get_team_id_by_name", return_value=66):
                # Remove venue from API response so it comes from cache
                match_data = {**sample_match_data}
                del match_data["venue"]
                mock_response = mock_api_response(200, {"matches": [match_data]})

                with patch.object(client.session, "get", return_value=mock_response):
                    result = client.fetch_fixtures("Manchester United")

                assert result[0].venue == "Old Trafford"
