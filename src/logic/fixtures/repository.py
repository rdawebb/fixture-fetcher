"""Repository protocol for accessing fixture data."""

from typing import List, Optional, Protocol

from logic.fixtures.models import Fixture


class FixtureRepository(Protocol):
    """Protocol for a repository that provides access to fixtures."""

    def fetch_fixtures(
        self,
        team_name: str,
        competitions: Optional[List[str]] = None,
        season: Optional[int] = None,
    ) -> List[Fixture]:
        """Fetch fixtures for a given team, optionally filtered by competitions and season.

        Args:
            team_name (str): The name of the team to fetch fixtures for.
            competitions (Optional[List[str]]): A list of competition codes to filter fixtures.
            season (Optional[int]): The season year to filter fixtures.

        Returns:
            List[Fixture]: A list of Fixture objects matching the criteria.
        """
        ...
