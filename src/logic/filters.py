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
    def only_home(fixtures: Iterable[Fixture]) -> List[Fixture]:
        """Filter fixtures to include only home games.

        Args:
            fixtures (Iterable[Fixture]): An iterable of Fixture objects.

        Returns:
            List[Fixture]: A list of Fixture objects that are home games.
        """
        try:
            result = (f for f in fixtures if f.is_home)
            logger.info(f"Filtered {len(list(result))} home fixtures from {len(list(fixtures))} total fixtures.")
            return result
        except AttributeError as e:
            logger.error(f"Error filtering home fixtures: {e}")
            raise DataProcessingError("Failed to filter home fixtures", context=e)

    @staticmethod
    def only_away(fixtures: Iterable[Fixture]) -> List[Fixture]:
        """Filter fixtures to include only away games.

        Args:
            fixtures (Iterable[Fixture]): An iterable of Fixture objects.

        Returns:
            List[Fixture]: A list of Fixture objects that are away games.
        """
        try:
            result = (f for f in fixtures if not f.is_home)
            logger.info(f"Filtered {len(list(result))} away fixtures from {len(list(fixtures))} total fixtures.")
            return result
        except AttributeError as e:
            logger.error(f"Error filtering away fixtures: {e}")
            raise DataProcessingError("Failed to filter away fixtures", context=e)

    @staticmethod
    def only_scheduled(fixtures: Iterable[Fixture]) -> List[Fixture]:
        """Filter fixtures to include only scheduled games.

        Args:
            fixtures (Iterable[Fixture]): An iterable of Fixture objects.

        Returns:
            List[Fixture]: A list of Fixture objects that are scheduled.
        """
        try:
            result = (f for f in fixtures if f.status in ('SCHEDULED', 'TIMED'))
            logger.info(f"Filtered {len(list(result))} scheduled fixtures from {len(list(fixtures))} total fixtures.")
            return result
        except AttributeError as e:
            logger.error(f"Error filtering scheduled fixtures: {e}")
            raise DataProcessingError("Failed to filter scheduled fixtures", context=e)

    @staticmethod
    def only_televised(fixtures: Iterable[Fixture]) -> List[Fixture]:
        """Filter fixtures to include only televised games.

        Args:
            fixtures (Iterable[Fixture]): An iterable of Fixture objects.

        Returns:
            List[Fixture]: A list of Fixture objects that are televised.
        """
        try:
            result = (f for f in fixtures if f.tv is not None)
            logger.info(f"Filtered {len(list(result))} televised fixtures from {len(list(fixtures))} total fixtures.")
            return result
        except AttributeError as e:
            logger.error(f"Error filtering televised fixtures: {e}")
            raise DataProcessingError("Failed to filter televised fixtures", context=e)

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
            result = (f for f in fixtures if f.competition_code == comp_code)
            logger.info(f"Filtered {len(list(result))} fixtures for competition {comp_code}.")
            return result
        except AttributeError as e:
            logger.error(f"Error filtering fixtures by competition: {e}")
            raise DataProcessingError("Failed to filter fixtures by competition", context=e)

    @staticmethod
    def by_date_range(fixtures: Iterable[Fixture], start_date: datetime, end_date: datetime) -> List[Fixture]:
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
            result = (f for f in fixtures if f.utc_kickoff is not None and start_date <= f.utc_kickoff <= end_date)
            logger.info(f"Filtered {len(list(result))} fixtures from {len(list(fixtures))} total fixtures.")
            return result
        except AttributeError as e:
            logger.error(f"Error filtering fixtures by date range: {e}")
            raise DataProcessingError("Failed to filter fixtures by date range", context=e)