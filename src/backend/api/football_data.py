"""Client for Football Data API."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, cast

import requests
import yaml

from backend.config import get_config
from logic.fixtures.models import Fixture
from utils import (
    APIError,
    AuthenticationError,
    ConnectionError,
    FFLogger,
    NotFoundError,
    ParsingError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
    TimeoutError,
    UnknownAPIError,
)

logger = FFLogger.get_logger(__name__)

config = get_config()
API = config["FOOTBALL_DATA_API"]
FOOTBALL_DATA_API_TOKEN = config["FOOTBALL_DATA_API_TOKEN"]
CACHE_PATH = Path(config["CACHE_PATH"])
COMP_CODES = config.get("FD_COMPETITIONS", {"PL": "Premier League"})

REQUEST_TIMEOUT = 30

HTTP_ERROR_MAP: dict[int, tuple] = {
    404: (NotFoundError, "warning"),
    429: (RateLimitError, "warning"),
    503: (ServiceUnavailableError, "error"),
}


class FDClient:
    """Low-level client for interacting with the Football Data API.

    Attributes:
        session: Requests session with authentication headers.
    """

    def __init__(self) -> None:
        """Initialise the Football Data API client.

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
        self._matches_cache: dict[tuple[str, int | None], tuple[dict, list[dict]]] = {}
        self._index: dict[str, dict] | None = None
        logger.debug("FDClient initialised successfully")

    def _team_index(self) -> dict[str, dict]:
        """Build a lowercase name lookup over the team cache.

        Both full names and short names are keys, with full names taking precedence
        where a short name collides with another team's full name.

        Returns:
            A dictionary mapping lowercased team names to their cached info.
        """
        if self._index is None:
            index: dict[str, dict] = {}
            for teams in self.cache.values():
                if not isinstance(teams, dict):
                    continue

                for name, info in teams.items():
                    short_name = info.get("short_name") or name
                    index[str(short_name).lower()] = info

            for teams in self.cache.values():
                if not isinstance(teams, dict):
                    continue

                for name, info in teams.items():
                    index[str(name).lower()] = info

            self._index = index

        return self._index

    def _load_cache(self) -> dict[str, Any]:
        """Load team cache from cache_path.

        Returns:
            A dictionary mapping team names to their IDs.
        """
        if self.cache_path.exists() and self.cache_path.is_file():
            try:
                data = yaml.safe_load(self.cache_path.read_text()) or {}
                num_teams = sum(
                    len(teams) if isinstance(teams, dict) else 0
                    for teams in data.values()
                )
                logger.info(f"Loaded {num_teams} team IDs from cache")
                return data

            except yaml.YAMLError as e:
                logger.error(f"Failed to load cache: {e}")
                return {}

        return {}

    def _save_cache(self) -> None:
        """Save team cache to cache_path."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            if self.cache_path.exists() and self.cache_path.is_dir():
                logger.error("Cache path is a directory, not a file")
                return

            # Validate cache structure before saving
            if not isinstance(self.cache, dict):
                logger.error(
                    f"Invalid cache structure: expected dict, got {type(self.cache).__name__}"
                )
                return

            for league, teams in self.cache.items():
                if not isinstance(teams, dict):
                    logger.error(
                        f"Invalid cache structure for league '{league}': expected dict, got {type(teams).__name__}"
                    )
                    return

            self.cache_path.write_text(yaml.safe_dump(self.cache, sort_keys=True))
            logger.debug("Cache saved successfully")
            print("💾 Saved team cache successfully")

        except yaml.YAMLError as e:
            logger.error(f"Failed to save cache: {e}")

    def _add_to_cache(
        self,
        league: str,
        team_name: str,
        team_id: int,
        short_name: str | None = None,
        venue: str | None = None,
    ) -> None:
        """Add a team to the cache and save it.

        Args:
            league: The league name.
            team_name: Name of the team.
            team_id: ID of the team.
            short_name: Short name of the team.
            venue: Stadium/venue name for the team.
        """
        if league not in self.cache:
            self.cache[league] = {}

        normalised_name = team_name.title()
        self.cache[league][normalised_name] = {
            "id": team_id,
            "short_name": short_name or normalised_name,
        }

        if venue:
            self.cache[league][normalised_name]["venue"] = venue

        self._index = None
        self._save_cache()

    def refresh_team_cache(
        self, competitions: list[str] | None = None, cache_path: Path | None = None
    ) -> None:
        """Refresh the team cache by fetching teams from specified competitions.

        Args:
            competitions: List of competition codes to fetch teams from.
            cache_path: Optional path to save the cache to. If not provided, uses default CACHE_PATH.
        """
        if cache_path:
            self.cache_path = cache_path

        comps = competitions if competitions else list(COMP_CODES.keys())
        all_teams: dict[str, Any] = {}

        for code in comps:
            try:
                response = self.session.get(
                    f"{API}competitions/{code}/teams", headers=self.token, timeout=30
                )
                response.raise_for_status()
                data = self._handle_response(response, f"teams for competition {code}")

                league_name = COMP_CODES.get(code, code)
                if league_name not in all_teams:
                    all_teams[league_name] = {}

                for team in data.get("teams", []):
                    all_teams[league_name][team["name"]] = {
                        "id": team["id"],
                        "short_name": team.get("shortName", team["name"]),
                        "venue": team.get("venue"),
                        "club_colors": team.get("clubColors"),
                        "crest": team.get("crest"),
                    }

            except Exception as e:
                logger.error(f"Failed to refresh team cache: {e}")
                raise ConnectionError(
                    f"Failed to refresh team cache for competition {code}: {e}"
                ) from e

        if all_teams:
            # Merge per league so refreshing one competition leaves the others intact
            for league_name, teams in all_teams.items():
                self.cache[league_name] = teams

            self._index = None
            self._save_cache()
            num_teams = sum(len(teams) for teams in all_teams.values())
            logger.info(
                f"Refreshed team cache with {num_teams} teams across {len(all_teams)} league(s)"
            )
            print(f"🔄 Refreshed team cache with {num_teams} teams")

        else:
            logger.warning("No teams fetched to refresh cache")
            print("⚠️ No teams fetched to refresh cache")

    def _handle_response(self, response: requests.Response, context: str = "") -> dict:
        """Handle API response and raise appropriate exceptions.

        Args:
            response: The HTTP response from the API.
            context: Contextual information for logging.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            APIError subclasses based on HTTP status codes.
        """
        status = response.status_code

        if status is not None:
            if status in HTTP_ERROR_MAP:
                exc_class, log_level = HTTP_ERROR_MAP[status]
                getattr(logger, log_level)(f"{exc_class.__name__}: {context}")
                raise exc_class(
                    str(exc_class.__doc__), status_code=status, response=response
                )

            elif status >= 500:
                logger.error(f"Server error occurred: {status}")
                raise ServerError("Server error", status_code=status, response=response)

            elif status >= 400:
                logger.error(f"Unknown API error occurred: {status}")
                raise UnknownAPIError(
                    "API error", status_code=status, response=response
                )

        try:
            data = response.json()

        except ValueError as e:
            logger.error(f"ParsingError: Failed to parse API response: {e}")
            raise ParsingError(
                f"Failed to parse API response: {e}", response=response
            ) from e

        if not isinstance(data, dict):
            error_msg = "Expected JSON response to be a dict"
            logger.error(f"ParsingError: Failed to parse API response: {error_msg}")
            raise ParsingError(
                f"Failed to parse API response: {error_msg}", response=response
            )

        return data

    def fetch_competition_matches(
        self, comp_code: str, season: int | None = None
    ) -> tuple[dict, list[dict]]:
        """Fetch every match in a competition, memoised per (competition, season).

        One request serves every team in the competition, so callers should share a
        single client for the whole build rather than creating one per team.

        Args:
            comp_code: Competition code (e.g. 'PL').
            season: Season year to filter matches.

        Returns:
            A tuple of (competition metadata, list of raw match dictionaries).

        Raises:
            TimeoutError: If the request times out.
            ConnectionError: If a network error occurs.
            APIError: Subclasses raised by _handle_response for HTTP errors.
        """
        key = (comp_code, season)
        if key in self._matches_cache:
            logger.debug(f"Using memoised {comp_code} matches")
            return self._matches_cache[key]

        params: dict[str, Any] = {"season": season} if season else {}
        context = f"matches for competition {comp_code}"

        try:
            logger.debug(f"Fetching {context} with params: {params}")
            print(f"📡 Fetching all {comp_code} matches...")
            response = self.session.get(
                f"{API}competitions/{comp_code}/matches",
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            data = self._handle_response(response, context)

        except requests.exceptions.Timeout:
            logger.error(f"TimeoutError: Request timed out fetching {context}")
            raise TimeoutError(f"Request timed out fetching {context}") from None

        except requests.exceptions.ConnectionError as e:
            logger.error(f"ConnectionError: Network error fetching {context}: {e}")
            raise ConnectionError(f"Network error fetching {context}") from e

        except APIError:
            raise  # Typed HTTP errors from _handle_response keep their identity

        except Exception as e:
            raise ConnectionError(f"Network error fetching {context}: {e}") from e

        comp_meta = data.get("competition") or {"code": comp_code, "name": comp_code}
        matches = data.get("matches", [])

        # Only successes are memoised: a transient 429 must not poison the build
        self._matches_cache[key] = (comp_meta, matches)
        logger.info(f"Fetched {len(matches)} {comp_code} matches in one request")
        return comp_meta, matches

    @staticmethod
    def _find_team_in_matches(matches: list[dict], team_name: str) -> dict | None:
        """Find a team in a competition's matches by name, short name or TLA.

        Args:
            matches: Raw match dictionaries from the API.
            team_name: Name of the team to search for.

        Returns:
            The matching team dictionary, or None if not present.
        """
        wanted = team_name.lower()
        if not wanted:
            return None

        for m in matches:
            for side in ("homeTeam", "awayTeam"):
                team = m.get(side) or {}
                names = {
                    str(team.get(key) or "").lower()
                    for key in ("name", "shortName", "tla")
                }
                if wanted in names - {""} and team.get("id") is not None:
                    return team

        return None

    def get_team_id_by_name(
        self,
        team_name: str,
        competitions: list[str] | None = None,
        season: int | None = None,
    ) -> int:
        """Get the team ID for a given team.

        Checks the team cache first. On a miss the team is resolved from the
        competition match payloads, which carry every team's id, name, short name
        and TLA, so the lookup costs no extra request beyond the one the fixture
        fetch needs anyway.

        Args:
            team_name: Name of the team to search for.
            competitions: Competition codes to search. Defaults to all configured.
            season: Season year to filter matches.

        Returns:
            The team ID as an integer.

        Raises:
            NotFoundError: If the team is not found in any searched competition.
        """
        info = self._team_index().get(team_name.lower())
        if info is not None:
            return int(info["id"])

        comps = competitions if competitions else list(COMP_CODES.keys())
        print(f"🔍 {team_name} not found in cache - resolving from match data...")

        for code in comps:
            _, matches = self.fetch_competition_matches(code, season)
            team = self._find_team_in_matches(matches, team_name)
            if team is None:
                continue

            team_id = cast(int, team["id"])
            self._add_to_cache(
                COMP_CODES.get(code, code),
                team["name"],
                team_id,
                team.get("shortName") or team["name"],
            )
            logger.info(
                f"Resolved and cached team ID for '{team_name}' from {code}: {team_id}"
            )
            print(f"🔄 Resolved and cached team ID for '{team_name}': {team_id}")
            return team_id

        logger.error(f"Team '{team_name}' not found in competitions {comps}")
        raise NotFoundError(f"Team '{team_name}' not found")

    def _to_fixture(
        self, m: dict, team_id: int, comp_meta: dict, comp_code: str
    ) -> Fixture:
        """Build a Fixture from a raw match dictionary.

        Args:
            m: The raw match dictionary from the API.
            team_id: ID of the team the fixture is being built for.
            comp_meta: Competition metadata to fall back on.
            comp_code: The competition code the match was fetched under.

        Returns:
            The corresponding Fixture.
        """
        comp = m.get("competition") or comp_meta
        match_id = str(m["id"])

        try:
            utc_kickoff = (
                dt.datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
                if m.get("utcDate")
                else None
            )

        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse kickoff time for match {match_id}: {e}")
            utc_kickoff = None

        home = m["homeTeam"]
        away = m["awayTeam"]
        venue_info = self._team_index().get(str(home.get("name") or "").lower())

        return Fixture(
            id=match_id,
            competition=comp.get("name", comp_code),
            competition_code=comp.get("code", comp_code),
            matchday=m.get("matchday"),
            utc_kickoff=utc_kickoff,
            home_team=home.get("shortName") or home.get("name", ""),
            away_team=away.get("shortName") or away.get("name", ""),
            venue=venue_info.get("venue") if venue_info else None,
            status=m["status"],
            tv=None,
            # Match on ID, not name: the caller's spelling need not match the API's
            is_home=home.get("id") == team_id,
        )

    def fetch_fixtures(
        self,
        team_name: str,
        competitions: list[str] | None = None,
        season: int | None = None,
    ) -> list[Fixture]:
        """Fetch fixtures for a given team.

        Fixtures are filtered out of the per-competition match payloads rather than
        requested per team, so a full multi-team build costs one request per
        competition rather than one per team.

        Args:
            team_name: Name of the team to fetch fixtures for.
            competitions: List of competition codes to fetch fixtures from.
            season: Season year to filter fixtures.

        Returns:
            List of fixtures for the specified team.
        """
        logger.info(f"Fetching fixtures for team: {team_name}")
        comps = competitions if competitions else list(COMP_CODES.keys())
        team_id = self.get_team_id_by_name(team_name, comps, season)

        info = self._team_index().get(team_name.lower())
        display_name = (info.get("short_name") if info else None) or team_name

        fixtures: list[Fixture] = []

        for code in comps:
            comp_meta, matches = self.fetch_competition_matches(code, season)
            logger.debug(f"Filtering {len(matches)} {code} matches for '{team_name}'")

            for m in matches:
                comp = m.get("competition") or comp_meta

                # Belt-and-braces: the endpoint is competition-scoped already
                if comp.get("code") and comp["code"] != code:
                    logger.debug(
                        f"Skipping match {m['id']} - competition {comp['code']} "
                        f"not in allowed set"
                    )
                    continue

                if team_id not in (m["homeTeam"].get("id"), m["awayTeam"].get("id")):
                    continue

                fixtures.append(self._to_fixture(m, team_id, comp_meta, code))

        logger.info(f"Fetched {len(fixtures)} fixtures for team '{team_name}'")
        print(f"📅 Fetched {len(fixtures)} fixtures for {display_name}")
        return fixtures


class FootballDataRepository:
    """Repository implementation using Football Data API."""

    def __init__(self, client: FDClient | None = None) -> None:
        """Initialise the repository with an FDClient instance.

        Args:
            client: An optional FDClient instance. If not provided, a new one is created.
        """
        self.client = client or FDClient()

    def fetch_fixtures(
        self,
        team_name: str,
        competitions: list[str] | None = None,
        season: int | None = None,
    ) -> list[Fixture]:
        """Fetch fixtures for a given team.

        Args:
            team_name: The name of the team to fetch fixtures for.
            competitions: An optional list of competition codes to filter fixtures.
            season: An optional season year to filter fixtures.

        Returns:
            A list of Fixture objects matching the criteria.
        """
        return self.client.fetch_fixtures(
            team_name,
            competitions,
            season,
        )
