"""Generate a YAML template for fixture overrides with empty TV fields."""

from pathlib import Path

import yaml

from src.logic.filters import Filter
from src.providers.football_data import FDClient

team = "Manchester United FC"

client = FDClient()
fixtures = client.fetch_fixtures(team, ["PL"], season=None)
fixtures = Filter.apply_filters(fixtures, scheduled_only=True)

output = {}
for f in fixtures:
    key = f"{f.id}@fixture-fetcher"
    game = f"{f.home_team} vs {f.away_team}"
    output[str(key)] = {
        "game": game,
        "date": f.utc_kickoff.strftime("%Y-%m-%d %H:%M") if f.utc_kickoff else "",
        "tv": "",
    }

Path("data/tv_overrides.yaml").write_text(yaml.safe_dump(output))
print("Wrote overrides template to data/tv_overrides.yaml")
