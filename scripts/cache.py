"""Script to update the Fixture Fetcher team cache"""

from src.app.cli import cache_teams

if __name__ == "__main__":
    cache_teams(competitions=["PL"])
