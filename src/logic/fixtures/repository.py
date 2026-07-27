"""Repository protocol for accessing fixture data."""

from typing import Protocol

from logic.fixtures.models import Fixture


class FixtureRepository(Protocol):
    """Protocol for a repository that provides access to fixtures."""

    def fetch_fixtures(
        self,
        team_name: str,
        competitions: list[str] | None = None,
        season: int | None = None,
    ) -> list[Fixture]:
        """Fetch fixtures for a given team, optionally filtered by competitions and season.

        Args:
            team_name: The name of the team to fetch fixtures for.
            competitions: A list of competition codes to filter fixtures.
            season: The season year to filter fixtures.

        Returns:
            A list of Fixture objects matching the criteria.
        """
        ...
