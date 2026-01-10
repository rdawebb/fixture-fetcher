"""Script to update the Fixture Fetcher team cache"""

from app.cli import cache_teams

if __name__ == "__main__":
    cache_teams(competitions=["PL"])
