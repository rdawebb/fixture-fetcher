"""Data models for football fixtures."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Fixture:
    """Data class representing a football fixture.
    
    Attributes:
        id: Unique identifier for the match.
        competition: Full name of the competition.
        competition_code: Short code for the competition (e.g., 'PL', 'CL').
        matchday: The matchday/round number, if applicable.
        utc_kickoff: Scheduled kick-off time in UTC.
        home_team: Name of the home team.
        away_team: Name of the away team.
        venue: Stadium name or venue, if available.
        status: Current status of the match (e.g., 'SCHEDULED', 'LIVE', 'FINISHED').
        tv: TV broadcaster information, if available.
        is_home: Whether the fixture is a home match for the team of interest.
    """
    id: str
    competition: str
    competition_code: str
    matchday: Optional[int]
    utc_kickoff: Optional[datetime]
    home_team: str
    away_team: str
    venue: Optional[str]
    status: str
    tv: Optional[str]
    is_home: bool

    def __str__(self) -> str:
        """Return a human-readable representation of the fixture."""
        home_away = "vs" if self.is_home else "@"
        return f"{self.home_team} {home_away} {self.away_team} ({self.competition})"