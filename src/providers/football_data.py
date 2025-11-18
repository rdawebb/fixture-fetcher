"""Client for Football Data API v4."""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path
from typing import Optional, cast

import requests
import yaml

from src.config import CACHE_PATH, FOOTBALL_DATA_API, FOOTBALL_DATA_API_TOKEN
from src.models import Fixture
from src.utils.errors import (
    AuthenticationError,
    ConnectionError,
    NotFoundError,
    ParsingError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
    TimeoutError,
    UnknownAPIError,
)

logger = logging.getLogger(__name__)

API = FOOTBALL_DATA_API

COMP_CODES: dict[str, str] = {
    "PL": "Premier League",
    "FA": "FA Cup",
    "EC": "EFL Cup",
    "CL": "Champions League",
    "EL": "Europa League",
    "UEL": "Europa Conference League",
}

HTTP_ERROR_MAP: dict[int, tuple] = {
    404: (NotFoundError, "warning"),
    429: (RateLimitError, "warning"),
    503: (ServiceUnavailableError, "error"),
}


class FDClient:
    """
    Client for interacting with the Football Data API.

    Attributes:
        session: Requests session with authentication headers.
    """

    def __init__(self) -> None:
        """
        Initialise the Football Data API client.

        Raises:
            AuthenticationError: If FOOTBALL_DATA_API_TOKEN is not set.
        """
        token = FOOTBALL_DATA_API_TOKEN
        if not token:
            logger.error("FOOTBALL_DATA_API_TOKEN environment variable not set")
            raise AuthenticationError("FOOTBALL_DATA_API_TOKEN not set")

        self.token = {"X-Auth-Token": token}
        self.session = requests.Session()
        self.session.headers.update(self.token)
        self.cache_path = CACHE_PATH
        self.cache = self._load_cache()
        logger.debug("FDClient initialized successfully")

    def _load_cache(self) -> dict[str, int]:
        """
        Load team cache from cache_path.

        Returns:
            A dictionary mapping team names to their IDs.
        """
        if self.cache_path.exists() and self.cache_path.is_file():
            try:
                data = yaml.safe_load(self.cache_path.read_text()) or {}
                print(f"🗂️ Loaded {len(data)} team IDs from cache")
                return data
            except yaml.YAMLError as e:
                logger.error(f"Failed to load cache from {self.cache_path}: {e}")
                print(f"⚠️ Failed to read from cache: {e}")
                return {}
        return {}

    def _save_cache(self) -> None:
        """
        Save team cache to cache_path.
        """
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            if self.cache_path.exists() and self.cache_path.is_dir():
                logger.error(f"Cache path {self.cache_path} is a directory, not a file")
                print(f"⚠️ Cache path {self.cache_path} is a directory, not a file")
                return
            self.cache_path.write_text(yaml.safe_dump(self.cache, sort_keys=True))
            logger.debug(f"Cache saved to {self.cache_path}")
            print(f"💾 Saved team cache to {self.cache_path}")
        except yaml.YAMLError as e:
            logger.error(f"Failed to save cache to {self.cache_path}: {e}")

    def _add_to_cache(self, team_name: str, team_id: int) -> None:
        """
        Add a team to the cache and save it.

        Args:
            team_name: Name of the team.
            team_id: ID of the team.
        """
        normalised_name = team_name.title()
        self.cache[normalised_name] = team_id
        self._save_cache()

    def refresh_team_cache(
        self, competitions: list[str] | None = None, cache_path: Optional[Path] = None
    ) -> None:
        """
        Refresh the team cache by fetching teams from specified competitions.

        Args:
            competitions: List of competition codes to fetch teams from.
            cache_path: Optional path to save the cache to. If not provided, uses default CACHE_PATH.
        """
        if cache_path:
            self.cache_path = cache_path

        comps = competitions if competitions else list(COMP_CODES.keys())
        all_teams: dict[str, int] = {}

        for code in comps:
            try:
                response = self.session.get(
                    f"{API}competitions/{code}/teams", headers=self.token, timeout=30
                )
                response.raise_for_status()
                data = self._handle_response(response, f"teams for competition {code}")

                data_teams = data.get("teams", [])
                for team in data_teams:
                    all_teams[team["name"]] = team["id"]
            except Exception as e:
                logger.error(f"{code} - Failed to refresh team cache: {e}")
                print(f"⚠️ {code}: failed to refresh team cache: {e}")
                raise ConnectionError(
                    f"Failed to refresh team cache for competition {code}: {e}"
                ) from e

        if all_teams:
            self.cache = all_teams
            self._save_cache()
            logger.info(f"Refreshed team cache with {len(all_teams)} teams")
            print(f"🔄 Refreshed team cache with {len(all_teams)} teams")
        else:
            logger.warning("No teams fetched to refresh cache")
            print("⚠️ No teams fetched to refresh cache")

    def _handle_response(self, response: requests.Response, context: str = "") -> dict:
        """
        Handle API response and raise appropriate exceptions.

        Args:
            response: The HTTP response from the API.
            context: Contextual information for logging.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            APIError subclasses based on HTTP status codes.
        """
        status = response.status_code

        if status in HTTP_ERROR_MAP:
            exc_class, log_level = HTTP_ERROR_MAP[status]
            getattr(logger, log_level)(f"{exc_class.__name__}: {context}")
            raise exc_class(str(exc_class.__doc__), status_code=status, response=response)

        if status >= 500:
            logger.error(f"ServerError: {context} (status: {status})")
            raise ServerError("Server error", status_code=status, response=response)
        elif status >= 400:
            logger.error(f"UnknownAPIError: {context} (status: {status})")
            raise UnknownAPIError("API error", status_code=status, response=response)

        try:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Expected JSON response to be a dict")
            return data
        except ValueError as e:
            logger.error(f"ParsingError: Failed to parse API response: {e}")
            raise ParsingError(f"Failed to parse API response: {e}", response=response) from e

    def get_team_id_by_name(self, team_name: str) -> int:
        """
        Get the team ID for a given team.

        Args:
            team_name: Name of the team to search for.

        Returns:
            The team ID as an integer.

        Raises:
            NotFoundError: If the team is not found.
        """
        # Check cache first (case-insensitive lookup)
        for cached_name, team_id in self.cache.items():
            if cached_name.lower() == team_name.lower():
                logger.info(f"Found team ID for '{team_name}' in cache: {team_id}")
                print(f"✅ Found team ID for '{team_name}' in cache: {team_id}")
                return team_id

        print(f"🔍 {team_name} not found in cache - fetching from football-data.org...")
        try:
            response = self.session.get(
                f"{API}competitions/PL/teams", headers=self.token, timeout=30
            )
            response.raise_for_status()
            data = self._handle_response(response, "teams for competition PL")
        except requests.exceptions.Timeout:
            logger.error(
                f"TimeoutError: Request timed out while fetching team ID for '{team_name}'"
            )
            raise TimeoutError(
                f"Request timed out while fetching team ID for '{team_name}'"
            ) from None
        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"ConnectionError: Network error while fetching team ID for '{team_name}': {e}"
            )
        except Exception as e:
            raise ConnectionError(
                f"Network error while fetching team ID for '{team_name}': {e}"
            ) from e

        data_teams = data.get("teams", [])
        if not data_teams:
            logger.error("No teams data found in API response")
            raise NotFoundError("No teams data found in API response")

        for team in data_teams:
            if (
                team["name"].lower() == team_name.lower()
                or team["shortName"].lower() == team_name.lower()
            ):
                team_id = cast(int, team["id"])
                self._add_to_cache(team["name"], team_id)
                logger.info(f"Fetched and cached team ID for '{team_name}': {team_id}")
                print(f"🔄 Fetched and cached team ID for '{team_name}': {team_id}")
                return team_id

        logger.error(f"Team '{team_name}' not found in API response")
        raise NotFoundError(f"Team '{team_name}' not found")

    def fetch_fixtures(
        self,
        team_name: str,
        competitions: Optional[list[str]] = None,
        season: Optional[int] = None,
    ) -> list[Fixture]:
        """Fetch fixtures for a given team."""
        logger.info(f"Fetching fixtures for team: {team_name}")
        team_id = self.get_team_id_by_name(team_name)
        params = {}

        if season:
            params["season"] = season

        try:
            logger.debug(f"Fetching matches for team ID {team_id} with params: {params}")
            print(f"📡 Fetching matches for {team_name} (ID {team_id})...")
            response = self.session.get(f"{API}teams/{team_id}/matches", params=params, timeout=10)
            data = self._handle_response(response, f"matches for team ID {team_id}")
        except requests.exceptions.Timeout:
            logger.error(
                f"TimeoutError: Request timed out while fetching fixtures for team '{team_name}'"
            )
            raise TimeoutError(
                f"Request timed out while fetching fixtures for team '{team_name}'"
            ) from None
        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"ConnectionError: Network error while fetching fixtures for team '{team_name}': {e}"
            )
            raise ConnectionError(
                f"Network error while fetching fixtures for team '{team_name}'"
            ) from e

        matches = data.get("matches", [])
        fixtures: list[Fixture] = []
        allowed = set(competitions) if competitions else set(COMP_CODES.keys())

        logger.debug(f"Processing {len(matches)} matches, filtering for competitions: {allowed}")

        for m in matches:
            comp_name = m["competition"]["name"]
            comp_code = m["competition"]["code"]

            if comp_code not in allowed:
                logger.debug(
                    f"Skipping match {m['id']} - competition {comp_code} not in allowed set"
                )
                continue

            match_id = str(m["id"])
            status = m["status"]
            matchday = m.get("matchday")

            try:
                utc_kickoff = (
                    dt.datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
                    if m.get("utcDate")
                    else None
                )
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse kickoff time for match {match_id}: {e}")
                utc_kickoff = None

            home_team = m["homeTeam"]["shortName"]
            away_team = m["awayTeam"]["shortName"]
            is_home = home_team.lower() == team_name.lower()
            venue = m.get("venue")

            fixtures.append(
                Fixture(
                    id=match_id,
                    competition=comp_name,
                    competition_code=comp_code,
                    matchday=matchday,
                    utc_kickoff=utc_kickoff,
                    home_team=home_team,
                    away_team=away_team,
                    venue=venue,
                    status=status,
                    tv=None,
                    is_home=is_home,
                )
            )

        logger.info(f"Fetched {len(fixtures)} fixtures for team '{team_name}'")
        print(f"📅 Fetched {len(fixtures)} fixtures for {team_name}")
        return fixtures
