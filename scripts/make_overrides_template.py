"""Generate a YAML template for fixture overrides with empty TV fields."""

import yaml
from pathlib import Path

from src.logic.filters import Filter
from src.providers.football_data import FDClient

team = "Manchester United FC"

client = FDClient()
fixtures = client.fetch_fixtures(team, ["PL"], season=None)
fixtures = Filter.apply_filters(fixtures, scheduled_only=True)

output = {}
for f in fixtures:
    key = f.id
    game = f"{f.home_team} vs {f.away_team}"
    output[str(key)] = {
        "game": game,
        "tv": "",
    }

Path("data/overrides_template.yaml").write_text(yaml.safe_dump(output))
print("Wrote overrides template to data/overrides_template.yaml")
