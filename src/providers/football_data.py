"""Client for Football Data API v4."""

from __future__ import annotations

import datetime as dt
import logging
import requests
from typing import Optional

from src.models import Fixture
from src.config import FOOTBALL_DATA_API, FOOTBALL_DATA_API_TOKEN
from src.utils.errors import (
    AuthenticationError,
    NotFoundError,
    ServerError,
    TimeoutError,
    RateLimitError,
    ServiceUnavailableError,
    ParsingError,
    UnknownAPIError,
    ConnectionError as ConnectionErrorCustom,
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
        logger.debug("FDClient initialized successfully")

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
            return response.json()
        except ValueError as e:
            logger.error(f"ParsingError: Failed to parse API response: {e}")
            raise ParsingError(f"Failed to parse API response: {e}", response=response)

    def get_team_id(self, team_name: str) -> int:
        """
        Get the team ID for a given team.

        Args:
            team_name: Name of the team to search for.
        
        Returns:
            The team ID as an integer.

        Raises:
            NotFoundError: If the team is not found.
        """
        try:
            logger.debug(f"Fetching team ID for: {team_name}")
            response = self.session.get(f"{API}teams", params={"name": team_name}, timeout=10)
            data = self._handle_response(response, f"teams search for '{team_name}'")
        except requests.exceptions.Timeout:
            logger.error(f"TimeoutError: Request timed out while searching for team '{team_name}'")
            raise TimeoutError(f"Request timed out while searching for team '{team_name}'")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"ConnectionError: Network error while searching for team '{team_name}': {e}")
            raise ConnectionErrorCustom(f"Network error while searching for team '{team_name}'")

        teams = data.get("teams", [])

        # First pass: exact match
        for t in teams:
            if t["name"].lower() == team_name.lower() or t["shortName"].lower() == team_name.lower():
                logger.debug(f"Found exact match for team '{team_name}': ID {t['id']}")
                return t["id"]

        # Second pass: substring match
        for t in teams:
            if team_name.lower() in t["name"].lower() or team_name.lower() in t["shortName"].lower():
                logger.debug(f"Found substring match for team '{team_name}': ID {t['id']}")
                return t["id"]

        logger.warning(f"Team not found: {team_name}")
        raise NotFoundError(f"Team '{team_name}' not found")

    def fetch_fixtures(
        self,
        team_name: str,
        competitions: Optional[list[str]] = None,
        season: Optional[int] = None,
    ) -> list[Fixture]:
        """Fetch fixtures for a given team."""
        logger.info(f"Fetching fixtures for team: {team_name}")
        team_id = self.get_team_id(team_name)
        params = {}

        if season:
            params["season"] = season

        try:
            logger.debug(f"Fetching matches for team ID {team_id} with params: {params}")
            response = self.session.get(f"{API}teams/{team_id}/matches", params=params, timeout=10)
            data = self._handle_response(response, f"matches for team ID {team_id}")
        except requests.exceptions.Timeout:
            logger.error(f"TimeoutError: Request timed out while fetching fixtures for team '{team_name}'")
            raise TimeoutError(f"Request timed out while fetching fixtures for team '{team_name}'")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"ConnectionError: Network error while fetching fixtures for team '{team_name}': {e}")
            raise ConnectionErrorCustom(f"Network error while fetching fixtures for team '{team_name}'")

        matches = data.get("matches", [])
        fixtures: list[Fixture] = []
        allowed = set(competitions) if competitions else set(COMP_CODES.keys())

        logger.debug(f"Processing {len(matches)} matches, filtering for competitions: {allowed}")
        
        for m in matches:
            comp_name = m["competition"]["name"]
            comp_code = m["competition"]["code"]

            if comp_code not in allowed:
                logger.debug(f"Skipping match {m['id']} - competition {comp_code} not in allowed set")
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

            home_team = m["homeTeam"]["name"]
            away_team = m["awayTeam"]["name"]
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
        return fixtures
