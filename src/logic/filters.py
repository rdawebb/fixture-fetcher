"""Filter module for processing data."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, List

from src.models import Fixture
from src.utils.errors import DataProcessingError, InvalidInputError

logger = logging.getLogger(__name__)


class Filter:
    """Class for filtering fixtures based on various criteria."""

    @staticmethod
    def apply_filters(
        fixtures: Iterable[Fixture],
        scheduled_only: bool = False,
        home_only: bool = False,
        away_only: bool = False,
        televised_only: bool = False,
    ) -> List[Fixture]:
        """Apply multiple filters to fixtures at once.

        Args:
            fixtures: An iterable of Fixture objects.
            scheduled_only: Filter to only scheduled fixtures.
            home_only: Filter to only home fixtures.
            away_only: Filter to only away fixtures.
            televised_only: Filter to only televised fixtures.

        Returns:
            List[Fixture]: A list of Fixture objects matching all applied filters.
        """
        result = list(fixtures)

        if scheduled_only:
            result = Filter.only_scheduled(result)
        if home_only:
            result = Filter.only_home(result)
        if away_only:
            result = Filter.only_away(result)
        if televised_only:
            result = Filter.only_televised(result)

        return result

    @staticmethod
    def only_home(fixtures: Iterable[Fixture]) -> List[Fixture]:
        """Filter fixtures to include only home games.

        Args:
            fixtures (Iterable[Fixture]): An iterable of Fixture objects.

        Returns:
            List[Fixture]: A list of Fixture objects that are home games.
        """
        try:
            fixtures_list = list(fixtures)
            result = [f for f in fixtures_list if f.is_home]
            logger.info(
                f"Filtered {len(result)} home fixtures from {len(fixtures_list)} total fixtures."
            )
            return result
        except AttributeError as e:
            logger.error(f"Error filtering home fixtures: {e}")
            raise DataProcessingError("Failed to filter home fixtures", context=e) from e

    @staticmethod
    def only_away(fixtures: Iterable[Fixture]) -> List[Fixture]:
        """Filter fixtures to include only away games.

        Args:
            fixtures (Iterable[Fixture]): An iterable of Fixture objects.

        Returns:
            List[Fixture]: A list of Fixture objects that are away games.
        """
        try:
            fixtures_list = list(fixtures)
            result = [f for f in fixtures_list if not f.is_home]
            logger.info(
                f"Filtered {len(result)} away fixtures from {len(fixtures_list)} total fixtures."
            )
            return result
        except AttributeError as e:
            logger.error(f"Error filtering away fixtures: {e}")
            raise DataProcessingError("Failed to filter away fixtures", context=e) from e

    @staticmethod
    def only_scheduled(fixtures: Iterable[Fixture]) -> List[Fixture]:
        """Filter fixtures to include only scheduled games.

        Args:
            fixtures (Iterable[Fixture]): An iterable of Fixture objects.

        Returns:
            List[Fixture]: A list of Fixture objects that are scheduled.
        """
        try:
            fixtures_list = list(fixtures)
            result = [f for f in fixtures_list if f.status in ("SCHEDULED", "TIMED")]
            logger.info(
                f"Filtered {len(result)} scheduled fixtures from {len(fixtures_list)} total fixtures."
            )
            return result
        except AttributeError as e:
            logger.error(f"Error filtering scheduled fixtures: {e}")
            raise DataProcessingError("Failed to filter scheduled fixtures", context=e) from e

    @staticmethod
    def only_televised(fixtures: Iterable[Fixture]) -> List[Fixture]:
        """Filter fixtures to include only televised games.

        Args:
            fixtures (Iterable[Fixture]): An iterable of Fixture objects.

        Returns:
            List[Fixture]: A list of Fixture objects that are televised.
        """
        try:
            fixtures_list = list(fixtures)
            result = [f for f in fixtures_list if f.tv is not None]
            logger.info(
                f"Filtered {len(result)} televised fixtures from {len(fixtures_list)} total fixtures."
            )
            return result
        except AttributeError as e:
            logger.error(f"Error filtering televised fixtures: {e}")
            raise DataProcessingError("Failed to filter televised fixtures", context=e) from e

    @staticmethod
    def by_competition(fixtures: Iterable[Fixture], comp_code: str) -> List[Fixture]:
        """Filter fixtures by competition code.

        Args:
            fixtures (Iterable[Fixture]): An iterable of Fixture objects.
            comp_code (str): The competition code to filter by.

        Returns:
            List[Fixture]: A list of Fixture objects that match the competition code.
        """
        if comp_code is None or not isinstance(comp_code, str):
            logger.error("Invalid competition code provided for filtering.")
            raise InvalidInputError("Competition code must be a non-empty string.")

        try:
            fixtures_list = list(fixtures)
            result = [f for f in fixtures_list if f.competition_code == comp_code]
            logger.info(f"Filtered {len(result)} fixtures for competition {comp_code}.")
            return result
        except AttributeError as e:
            logger.error(f"Error filtering fixtures by competition: {e}")
            raise DataProcessingError("Failed to filter fixtures by competition", context=e) from e

    @staticmethod
    def by_date_range(
        fixtures: Iterable[Fixture], start_date: datetime, end_date: datetime
    ) -> List[Fixture]:
        """Filter fixtures within a specific date range.

        Args:
            fixtures (Iterable[Fixture]): An iterable of Fixture objects.
            start_date (datetime): The start date of the range.
            end_date (datetime): The end date of the range.

        Returns:
            List[Fixture]: A list of Fixture objects within the specified date range.
        """
        if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
            logger.error("Invalid date range provided for filtering.")
            raise InvalidInputError("Start date and end date must be datetime objects.")

        try:
            fixtures_list = list(fixtures)
            result = [
                f
                for f in fixtures_list
                if f.utc_kickoff is not None and start_date <= f.utc_kickoff <= end_date
            ]
            logger.info(
                f"Filtered {len(result)} fixtures from {len(fixtures_list)} total fixtures."
            )
            return result
        except AttributeError as e:
            logger.error(f"Error filtering fixtures by date range: {e}")
            raise DataProcessingError("Failed to filter fixtures by date range", context=e) from e
