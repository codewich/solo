import json
from functools import lru_cache
from pathlib import Path

from solo_api.models import Destination

SEED_PATH = Path(__file__).resolve().parents[4] / "data" / "destinations" / "europe-seed.json"


@lru_cache(maxsize=1)
def load_destinations() -> list[Destination]:
    raw = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return [Destination.model_validate(item) for item in raw]
