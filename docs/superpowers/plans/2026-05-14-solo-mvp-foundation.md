# Solo MVP Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working Solo vertical slice: monorepo tooling, a Next.js web app, a FastAPI backend, seeded destinations, multi-window recommendations, and a window-aware itinerary stub ready for AI integration.

**Architecture:** The repo has `apps/web` for the TypeScript frontend, `apps/api` for the Python API, `packages/shared` for shared schema notes, and `data/destinations` for curated seed data. The API owns recommendation logic and durable domain shapes; the frontend calls the API through a small client module and keeps onboarding/dashboard state locally until persistence and Google SSO are added in a later pass.

**Tech Stack:** Next.js, React, TypeScript, FastAPI, Pydantic, pytest, Vitest, React Testing Library, pnpm, Python 3.12, curated JSON seed data.

---

## Visual Baseline Update

The approved first UI direction is an interactive calendar plus interactive map workspace. The web app should not use a simple card-only landing page as the final shape. The first implementation can use a lightweight CSS-positioned mock Europe map instead of Mapbox or MapLibre, but the layout must have three coordinated areas:

- Left panel: home city, preference lens, excluded destinations, and a bank-holiday-aware calendar with multiple selected travel windows.
- Center map: destination pins for ranked recommendations, including a visible home-city marker.
- Right panel: ranked recommendations for the selected travel window, with scores, reasons, and caveats.

Clicking a travel window should change which recommendation group is emphasized. Clicking a destination pin or card can be a no-op in the first slice, but the UI should be structured so a detail drawer or itinerary preview can be added later. This visual baseline supersedes older card-only page snippets in Task 8 and Task 10.

---

## File Structure

- Create `package.json`: root workspace scripts for web tests, API tests, linting, formatting, and dev.
- Create `pnpm-workspace.yaml`: pnpm workspace definition.
- Create `README.md`: local setup, commands, and product summary.
- Modify `.gitignore`: ignore Node, Python, local env, build, and coverage artifacts.
- Create `apps/web/package.json`: Next.js app dependencies and scripts.
- Create `apps/web/next.config.ts`: Next.js config.
- Create `apps/web/tsconfig.json`: TypeScript config.
- Create `apps/web/vitest.config.ts`: frontend test config.
- Create `apps/web/src/app/layout.tsx`: app layout.
- Create `apps/web/src/app/page.tsx`: Solo first-screen experience.
- Create `apps/web/src/app/globals.css`: app styling.
- Create `apps/web/src/lib/api.ts`: typed browser API client.
- Create `apps/web/src/lib/types.ts`: frontend request and response types.
- Create `apps/web/src/lib/date-windows.ts`: date range duration helper.
- Create `apps/web/src/lib/date-windows.test.ts`: unit tests for date helper.
- Create `apps/web/src/app/page.test.tsx`: smoke test for onboarding/dashboard UI.
- Create `apps/api/pyproject.toml`: Python dependencies and pytest config.
- Create `apps/api/src/solo_api/__init__.py`: package marker.
- Create `apps/api/src/solo_api/main.py`: FastAPI app and route wiring.
- Create `apps/api/src/solo_api/models.py`: Pydantic domain models.
- Create `apps/api/src/solo_api/destinations.py`: seed-data loading.
- Create `apps/api/src/solo_api/holidays.py`: simple UK bank-holiday provider for first pass.
- Create `apps/api/src/solo_api/recommendations.py`: recommendation filtering and scoring.
- Create `apps/api/src/solo_api/itineraries.py`: deterministic window-aware itinerary draft.
- Create `apps/api/tests/test_recommendations.py`: backend recommendation tests.
- Create `apps/api/tests/test_holidays.py`: backend holiday tests.
- Create `apps/api/tests/test_itineraries.py`: backend itinerary tests.
- Create `data/destinations/europe-seed.json`: curated seed destinations.
- Create `packages/shared/README.md`: shared contract notes.

---

## Task 1: Root Monorepo Setup

**Files:**
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Modify: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Write root workspace files**

Create `package.json`:

```json
{
  "name": "solo",
  "version": "0.1.0",
  "private": true,
  "packageManager": "pnpm@9.15.4",
  "scripts": {
    "dev:web": "pnpm --filter @solo/web dev",
    "dev:api": "cd apps/api && uvicorn solo_api.main:app --reload --host 127.0.0.1 --port 8000",
    "test": "pnpm test:web && pnpm test:api",
    "test:web": "pnpm --filter @solo/web test",
    "test:api": "cd apps/api && pytest",
    "lint:web": "pnpm --filter @solo/web lint"
  }
}
```

Create `pnpm-workspace.yaml`:

```yaml
packages:
  - "apps/web"
  - "packages/*"
```

Update `.gitignore`:

```gitignore
.superpowers/
.env
.env.*
!.env.example
node_modules/
.next/
dist/
build/
coverage/
.pytest_cache/
.ruff_cache/
.mypy_cache/
__pycache__/
*.py[cod]
.venv/
```

Create `README.md`:

```markdown
# Solo

Solo is a planning-first travel web app for flexible solo travelers in Europe. It helps users choose destinations for bank holidays and other date ranges, compare multiple candidate travel windows, exclude places they have already visited, and draft window-aware itineraries.

## Apps

- `apps/web`: Next.js TypeScript frontend.
- `apps/api`: FastAPI Python backend.
- `data/destinations`: curated seed destination data.
- `packages/shared`: shared contract notes and generated artifacts when useful.

## Local Commands

```bash
pnpm install
pnpm dev:web
pnpm dev:api
pnpm test
```

The first milestone uses local browser state and deterministic API responses. Google SSO, Postgres persistence, live data providers, and flight monitoring come after the first vertical slice.
```

- [ ] **Step 2: Verify root files**

Run: `git status --short`

Expected: root workspace files appear as new or modified.

- [ ] **Step 3: Commit root setup**

```bash
git add package.json pnpm-workspace.yaml .gitignore README.md
git commit -m "chore: set up monorepo workspace"
```

---

## Task 2: FastAPI Project Skeleton

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/solo_api/__init__.py`
- Create: `apps/api/src/solo_api/main.py`
- Create: `apps/api/tests/test_health.py`

- [ ] **Step 1: Write the failing health test**

Create `apps/api/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from solo_api.main import app


def test_health_returns_ok():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "solo-api"}
```

- [ ] **Step 2: Run test to verify it fails before implementation**

Run: `cd apps/api && pytest tests/test_health.py -v`

Expected: FAIL because `solo_api.main` does not exist.

- [ ] **Step 3: Create API package and health route**

Create `apps/api/pyproject.toml`:

```toml
[project]
name = "solo-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "pydantic>=2.10.0",
  "uvicorn[standard]>=0.34.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "httpx>=0.28.0",
  "ruff>=0.8.0"
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"
```

Create `apps/api/src/solo_api/__init__.py`:

```python
"""Solo API package."""
```

Create `apps/api/src/solo_api/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Solo API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "solo-api"}
```

- [ ] **Step 4: Run health test to verify it passes**

Run: `cd apps/api && pytest tests/test_health.py -v`

Expected: PASS.

- [ ] **Step 5: Commit API skeleton**

```bash
git add apps/api
git commit -m "feat: add FastAPI skeleton"
```

---

## Task 3: Backend Domain Models

**Files:**
- Create: `apps/api/src/solo_api/models.py`
- Create: `apps/api/tests/test_models.py`

- [ ] **Step 1: Write failing model tests**

Create `apps/api/tests/test_models.py`:

```python
from datetime import date

import pytest
from pydantic import ValidationError

from solo_api.models import PreferenceProfile, TravelWindow


def test_travel_window_counts_inclusive_days():
    window = TravelWindow(id="may-bank", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25))

    assert window.duration_days == 3


def test_travel_window_rejects_end_before_start():
    with pytest.raises(ValidationError):
        TravelWindow(id="bad", start_date=date(2026, 5, 25), end_date=date(2026, 5, 23))


def test_preference_profile_defaults_are_balanced():
    profile = PreferenceProfile()

    assert profile.pace == "balanced"
    assert profile.budget_sensitivity == 3
    assert "food" in profile.interests
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && pytest tests/test_models.py -v`

Expected: FAIL because `solo_api.models` does not exist.

- [ ] **Step 3: Implement domain models**

Create `apps/api/src/solo_api/models.py`:

```python
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator

Pace = Literal["rushed", "balanced", "wandering"]


class TravelWindow(BaseModel):
    id: str
    start_date: date
    end_date: date
    label: str | None = None
    linked_holiday: str | None = None
    status: Literal["candidate", "planned", "archived"] = "candidate"

    @model_validator(mode="after")
    def ensure_valid_range(self) -> "TravelWindow":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self

    @computed_field
    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1


class PreferenceProfile(BaseModel):
    pace: Pace = "balanced"
    climate: Literal["cool", "mild", "warm", "any"] = "any"
    budget_sensitivity: int = Field(default=3, ge=1, le=5)
    popularity: Literal["popular", "underrated", "mix"] = "mix"
    interests: dict[str, int] = Field(
        default_factory=lambda: {
            "food": 3,
            "history": 3,
            "museums": 3,
            "nightlife": 2,
            "nature": 2,
            "architecture": 3,
        }
    )


class Destination(BaseModel):
    id: str
    city: str
    country: str
    timezone: str
    latitude: float
    longitude: float
    cost_level: int = Field(ge=1, le=5)
    short_stay_score: int = Field(ge=1, le=5)
    solo_friendliness: int = Field(ge=1, le=5)
    tags: list[str]
    seasonal_strengths: dict[str, list[str]]
    climate_notes: str
    caveats: list[str] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    home_city: str
    travel_windows: list[TravelWindow]
    preferences: PreferenceProfile = Field(default_factory=PreferenceProfile)
    excluded_destination_ids: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    travel_window_id: str
    destination: Destination
    score: int
    reasons: list[str]
    caveats: list[str]


class RecommendationGroup(BaseModel):
    travel_window: TravelWindow
    recommendations: list[Recommendation]
```

- [ ] **Step 4: Run model tests**

Run: `cd apps/api && pytest tests/test_models.py -v`

Expected: PASS.

- [ ] **Step 5: Commit domain models**

```bash
git add apps/api/src/solo_api/models.py apps/api/tests/test_models.py
git commit -m "feat: define travel domain models"
```

---

## Task 4: Seed Destination Provider

**Files:**
- Create: `data/destinations/europe-seed.json`
- Create: `apps/api/src/solo_api/destinations.py`
- Create: `apps/api/tests/test_destinations.py`

- [ ] **Step 1: Write failing destination provider tests**

Create `apps/api/tests/test_destinations.py`:

```python
from solo_api.destinations import load_destinations


def test_load_destinations_returns_seeded_cities():
    destinations = load_destinations()
    ids = {destination.id for destination in destinations}

    assert {"lisbon-pt", "porto-pt", "prague-cz", "copenhagen-dk", "seville-es"} <= ids


def test_destinations_include_recommendation_metadata():
    lisbon = next(destination for destination in load_destinations() if destination.id == "lisbon-pt")

    assert lisbon.short_stay_score >= 4
    assert "food" in lisbon.tags
    assert "spring" in lisbon.seasonal_strengths
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && pytest tests/test_destinations.py -v`

Expected: FAIL because `solo_api.destinations` does not exist.

- [ ] **Step 3: Create seed data**

Create `data/destinations/europe-seed.json`:

```json
[
  {
    "id": "lisbon-pt",
    "city": "Lisbon",
    "country": "Portugal",
    "timezone": "Europe/Lisbon",
    "latitude": 38.7223,
    "longitude": -9.1393,
    "cost_level": 3,
    "short_stay_score": 5,
    "solo_friendliness": 5,
    "tags": ["food", "architecture", "warm", "nightlife", "history", "slow-wander", "popular"],
    "seasonal_strengths": {
      "spring": ["mild weather", "long daylight", "outdoor viewpoints"],
      "summer": ["beach access", "late evenings"],
      "autumn": ["warm shoulder season", "food"],
      "winter": ["milder than northern Europe"]
    },
    "climate_notes": "Mild winters and warm summers; strong long-weekend fit outside peak heat.",
    "caveats": ["Hilly neighborhoods can make packed days tiring."]
  },
  {
    "id": "porto-pt",
    "city": "Porto",
    "country": "Portugal",
    "timezone": "Europe/Lisbon",
    "latitude": 41.1579,
    "longitude": -8.6291,
    "cost_level": 3,
    "short_stay_score": 5,
    "solo_friendliness": 4,
    "tags": ["food", "architecture", "history", "slow-wander", "underrated"],
    "seasonal_strengths": {
      "spring": ["river walks", "wine cellars", "mild days"],
      "summer": ["coastal day trips"],
      "autumn": ["harvest atmosphere", "food"],
      "winter": ["moody historic streets"]
    },
    "climate_notes": "Cooler and wetter than Lisbon, especially in winter.",
    "caveats": ["Rain is common in late autumn and winter."]
  },
  {
    "id": "prague-cz",
    "city": "Prague",
    "country": "Czechia",
    "timezone": "Europe/Prague",
    "latitude": 50.0755,
    "longitude": 14.4378,
    "cost_level": 3,
    "short_stay_score": 5,
    "solo_friendliness": 4,
    "tags": ["history", "architecture", "museums", "nightlife", "popular"],
    "seasonal_strengths": {
      "spring": ["walkable old town", "parks", "beer gardens"],
      "summer": ["long evenings", "riverfront"],
      "autumn": ["cool walking weather"],
      "winter": ["christmas-market", "atmospheric streets"]
    },
    "climate_notes": "Cold in winter, pleasant in spring and early autumn.",
    "caveats": ["Central areas can feel crowded on peak weekends."]
  },
  {
    "id": "copenhagen-dk",
    "city": "Copenhagen",
    "country": "Denmark",
    "timezone": "Europe/Copenhagen",
    "latitude": 55.6761,
    "longitude": 12.5683,
    "cost_level": 5,
    "short_stay_score": 4,
    "solo_friendliness": 5,
    "tags": ["food", "design", "museums", "cycling", "architecture", "popular"],
    "seasonal_strengths": {
      "spring": ["design", "harbor walks"],
      "summer": ["swimming spots", "long daylight", "cycling"],
      "autumn": ["food", "museums"],
      "winter": ["cosy cafes", "design shops"]
    },
    "climate_notes": "Best in late spring and summer; winter is cold and dark.",
    "caveats": ["Expensive compared with southern Europe."]
  },
  {
    "id": "seville-es",
    "city": "Seville",
    "country": "Spain",
    "timezone": "Europe/Madrid",
    "latitude": 37.3891,
    "longitude": -5.9845,
    "cost_level": 3,
    "short_stay_score": 5,
    "solo_friendliness": 4,
    "tags": ["warm", "food", "history", "architecture", "slow-wander", "underrated"],
    "seasonal_strengths": {
      "spring": ["orange blossoms", "festivals", "ideal walking weather"],
      "summer": ["late nights"],
      "autumn": ["warm evenings", "food"],
      "winter": ["mild city break"]
    },
    "climate_notes": "Excellent in spring and autumn; very hot in summer.",
    "caveats": ["Summer afternoons can be too hot for rushed sightseeing."]
  }
]
```

- [ ] **Step 4: Implement destination loader**

Create `apps/api/src/solo_api/destinations.py`:

```python
import json
from functools import lru_cache
from pathlib import Path

from solo_api.models import Destination

SEED_PATH = Path(__file__).resolve().parents[4] / "data" / "destinations" / "europe-seed.json"


@lru_cache(maxsize=1)
def load_destinations() -> list[Destination]:
    raw = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return [Destination.model_validate(item) for item in raw]
```

- [ ] **Step 5: Run destination tests**

Run: `cd apps/api && pytest tests/test_destinations.py -v`

Expected: PASS.

- [ ] **Step 6: Commit destination provider**

```bash
git add data/destinations/europe-seed.json apps/api/src/solo_api/destinations.py apps/api/tests/test_destinations.py
git commit -m "feat: add curated destination provider"
```

---

## Task 5: Holiday Provider

**Files:**
- Create: `apps/api/src/solo_api/holidays.py`
- Create: `apps/api/tests/test_holidays.py`

- [ ] **Step 1: Write failing holiday tests**

Create `apps/api/tests/test_holidays.py`:

```python
from solo_api.holidays import get_bank_holidays


def test_uk_2026_holidays_include_may_bank_holiday():
    holidays = get_bank_holidays(country="GB", year=2026)

    assert {"date": "2026-05-25", "name": "Spring bank holiday"} in holidays


def test_unknown_country_returns_empty_list():
    assert get_bank_holidays(country="ZZ", year=2026) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && pytest tests/test_holidays.py -v`

Expected: FAIL because `solo_api.holidays` does not exist.

- [ ] **Step 3: Implement simple holiday provider**

Create `apps/api/src/solo_api/holidays.py`:

```python
HOLIDAYS: dict[tuple[str, int], list[dict[str, str]]] = {
    ("GB", 2026): [
        {"date": "2026-01-01", "name": "New Year's Day"},
        {"date": "2026-04-03", "name": "Good Friday"},
        {"date": "2026-04-06", "name": "Easter Monday"},
        {"date": "2026-05-04", "name": "Early May bank holiday"},
        {"date": "2026-05-25", "name": "Spring bank holiday"},
        {"date": "2026-08-31", "name": "Summer bank holiday"},
        {"date": "2026-12-25", "name": "Christmas Day"},
        {"date": "2026-12-28", "name": "Boxing Day substitute"},
    ]
}


def get_bank_holidays(country: str, year: int) -> list[dict[str, str]]:
    return HOLIDAYS.get((country.upper(), year), [])
```

- [ ] **Step 4: Run holiday tests**

Run: `cd apps/api && pytest tests/test_holidays.py -v`

Expected: PASS.

- [ ] **Step 5: Commit holiday provider**

```bash
git add apps/api/src/solo_api/holidays.py apps/api/tests/test_holidays.py
git commit -m "feat: add bank holiday provider"
```

---

## Task 6: Recommendation Engine And Routes

**Files:**
- Create: `apps/api/src/solo_api/recommendations.py`
- Modify: `apps/api/src/solo_api/main.py`
- Create: `apps/api/tests/test_recommendations.py`

- [ ] **Step 1: Write failing recommendation tests**

Create `apps/api/tests/test_recommendations.py`:

```python
from datetime import date

from fastapi.testclient import TestClient

from solo_api.main import app
from solo_api.models import PreferenceProfile, RecommendationRequest, TravelWindow
from solo_api.recommendations import recommend_destinations


def test_recommendations_are_grouped_by_travel_window():
    request = RecommendationRequest(
        home_city="London",
        travel_windows=[
            TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25)),
            TravelWindow(id="august", start_date=date(2026, 8, 29), end_date=date(2026, 8, 31)),
        ],
        preferences=PreferenceProfile(climate="warm", interests={"food": 5, "history": 2}),
    )

    groups = recommend_destinations(request)

    assert [group.travel_window.id for group in groups] == ["may", "august"]
    assert all(group.recommendations for group in groups)


def test_recommendations_respect_exclusions():
    request = RecommendationRequest(
        home_city="London",
        travel_windows=[TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25))],
        excluded_destination_ids=["lisbon-pt", "seville-es"],
    )

    groups = recommend_destinations(request)
    destination_ids = {item.destination.id for item in groups[0].recommendations}

    assert "lisbon-pt" not in destination_ids
    assert "seville-es" not in destination_ids


def test_recommendations_endpoint_returns_groups():
    client = TestClient(app)

    response = client.post(
        "/recommendations",
        json={
            "home_city": "London",
            "travel_windows": [
                {"id": "may", "start_date": "2026-05-23", "end_date": "2026-05-25"}
            ],
            "preferences": {"pace": "wandering", "climate": "warm", "budget_sensitivity": 3},
            "excluded_destination_ids": ["prague-cz"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["travel_window"]["id"] == "may"
    assert body[0]["recommendations"][0]["destination"]["id"] != "prague-cz"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && pytest tests/test_recommendations.py -v`

Expected: FAIL because `solo_api.recommendations` does not exist or `/recommendations` is missing.

- [ ] **Step 3: Implement recommendation engine**

Create `apps/api/src/solo_api/recommendations.py`:

```python
from solo_api.destinations import load_destinations
from solo_api.models import Destination, Recommendation, RecommendationGroup, RecommendationRequest, TravelWindow


def season_for_month(month: int) -> str:
    if month in {3, 4, 5}:
        return "spring"
    if month in {6, 7, 8}:
        return "summer"
    if month in {9, 10, 11}:
        return "autumn"
    return "winter"


def score_destination(destination: Destination, window: TravelWindow, request: RecommendationRequest) -> tuple[int, list[str]]:
    score = destination.short_stay_score * 10 + destination.solo_friendliness * 5
    reasons: list[str] = []
    season = season_for_month(window.start_date.month)

    if season in destination.seasonal_strengths:
        score += 10
        reasons.append(f"Strong {season} fit: {', '.join(destination.seasonal_strengths[season][:2])}.")

    if request.preferences.climate == "warm" and "warm" in destination.tags:
        score += 12
        reasons.append("Matches your preference for warmer destinations.")

    if request.preferences.popularity == "underrated" and "underrated" in destination.tags:
        score += 8
        reasons.append("Leans toward a less obvious city break.")

    for interest, weight in request.preferences.interests.items():
        if interest in destination.tags:
            score += weight * 2
            reasons.append(f"Good match for {interest}.")

    if request.preferences.budget_sensitivity >= 4 and destination.cost_level >= 5:
        score -= 10
        reasons.append("Higher cost may matter for your budget setting.")

    if not reasons:
        reasons.append("Good short-stay fundamentals for this travel window.")

    return score, reasons[:4]


def recommend_destinations(request: RecommendationRequest) -> list[RecommendationGroup]:
    excluded = set(request.excluded_destination_ids)
    candidates = [destination for destination in load_destinations() if destination.id not in excluded]
    groups: list[RecommendationGroup] = []

    for window in request.travel_windows:
        ranked = []
        for destination in candidates:
            score, reasons = score_destination(destination, window, request)
            ranked.append(
                Recommendation(
                    travel_window_id=window.id,
                    destination=destination,
                    score=score,
                    reasons=reasons,
                    caveats=destination.caveats,
                )
            )
        ranked.sort(key=lambda item: item.score, reverse=True)
        groups.append(RecommendationGroup(travel_window=window, recommendations=ranked[:5]))

    return groups
```

- [ ] **Step 4: Wire recommendation route**

Modify `apps/api/src/solo_api/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from solo_api.holidays import get_bank_holidays
from solo_api.models import RecommendationGroup, RecommendationRequest
from solo_api.recommendations import recommend_destinations

app = FastAPI(title="Solo API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "solo-api"}


@app.get("/holidays")
def holidays(country: str = "GB", year: int = 2026) -> list[dict[str, str]]:
    return get_bank_holidays(country=country, year=year)


@app.post("/recommendations")
def recommendations(request: RecommendationRequest) -> list[RecommendationGroup]:
    return recommend_destinations(request)
```

- [ ] **Step 5: Run recommendation tests**

Run: `cd apps/api && pytest tests/test_recommendations.py -v`

Expected: PASS.

- [ ] **Step 6: Run all API tests**

Run: `cd apps/api && pytest -v`

Expected: PASS.

- [ ] **Step 7: Commit recommendation engine**

```bash
git add apps/api/src/solo_api/recommendations.py apps/api/src/solo_api/main.py apps/api/tests/test_recommendations.py
git commit -m "feat: recommend destinations by travel window"
```

---

## Task 7: Window-Aware Itinerary Route

**Files:**
- Create: `apps/api/src/solo_api/itineraries.py`
- Modify: `apps/api/src/solo_api/main.py`
- Create: `apps/api/tests/test_itineraries.py`

- [ ] **Step 1: Write failing itinerary tests**

Create `apps/api/tests/test_itineraries.py`:

```python
from datetime import date

from fastapi.testclient import TestClient

from solo_api.itineraries import build_itinerary
from solo_api.models import PreferenceProfile, TravelWindow


def test_itinerary_matches_window_duration():
    window = TravelWindow(id="long-weekend", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25))

    itinerary = build_itinerary(destination_city="Lisbon", window=window, preferences=PreferenceProfile(pace="wandering"))

    assert len(itinerary["days"]) == 3
    assert itinerary["pace"] == "wandering"


def test_itinerary_endpoint_returns_days():
    client = TestClient(__import__("solo_api.main", fromlist=["app"]).app)

    response = client.post(
        "/itineraries",
        json={
            "destination_city": "Porto",
            "travel_window": {"id": "porto-trip", "start_date": "2026-06-12", "end_date": "2026-06-15"},
            "preferences": {"pace": "balanced"}
        },
    )

    assert response.status_code == 200
    assert len(response.json()["days"]) == 4
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && pytest tests/test_itineraries.py -v`

Expected: FAIL because `solo_api.itineraries` does not exist.

- [ ] **Step 3: Implement itinerary builder**

Create `apps/api/src/solo_api/itineraries.py`:

```python
from pydantic import BaseModel

from solo_api.models import PreferenceProfile, TravelWindow


class ItineraryRequest(BaseModel):
    destination_city: str
    travel_window: TravelWindow
    preferences: PreferenceProfile = PreferenceProfile()


def build_itinerary(destination_city: str, window: TravelWindow, preferences: PreferenceProfile) -> dict:
    intensity = {
        "rushed": "Add one extra optional stop if energy is high.",
        "balanced": "Keep a comfortable rhythm with time for meals and transit.",
        "wandering": "Leave generous unscheduled time for neighborhoods and cafes.",
    }[preferences.pace]

    days = []
    for index in range(window.duration_days):
        day_number = index + 1
        days.append(
            {
                "day": day_number,
                "title": f"Day {day_number} in {destination_city}",
                "morning": f"Start with a central neighborhood walk in {destination_city}.",
                "afternoon": "Choose one anchor museum, market, viewpoint, or historic area.",
                "evening": "Pick a relaxed dinner area and keep the route walkable.",
                "pace_note": intensity,
            }
        )

    return {
        "destination_city": destination_city,
        "travel_window_id": window.id,
        "pace": preferences.pace,
        "days": days,
    }
```

- [ ] **Step 4: Wire itinerary route**

Modify `apps/api/src/solo_api/main.py` imports and routes:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from solo_api.holidays import get_bank_holidays
from solo_api.itineraries import ItineraryRequest, build_itinerary
from solo_api.models import RecommendationGroup, RecommendationRequest
from solo_api.recommendations import recommend_destinations
```

Add route:

```python
@app.post("/itineraries")
def itineraries(request: ItineraryRequest) -> dict:
    return build_itinerary(
        destination_city=request.destination_city,
        window=request.travel_window,
        preferences=request.preferences,
    )
```

- [ ] **Step 5: Run itinerary tests**

Run: `cd apps/api && pytest tests/test_itineraries.py -v`

Expected: PASS.

- [ ] **Step 6: Commit itinerary route**

```bash
git add apps/api/src/solo_api/itineraries.py apps/api/src/solo_api/main.py apps/api/tests/test_itineraries.py
git commit -m "feat: add window-aware itinerary route"
```

---

## Task 8: Next.js Calendar-Map Web Skeleton

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/globals.css`
- Create: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/app/page.test.tsx`

- [ ] **Step 1: Write failing page smoke test**

Create `apps/web/src/app/page.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import Page from "./page";

describe("Solo homepage", () => {
  it("renders the travel calendar map workflow", () => {
    render(<Page />);

    expect(screen.getByRole("heading", { name: "Solo" })).toBeInTheDocument();
    expect(screen.getByText("Long-weekend map planner")).toBeInTheDocument();
    expect(screen.getByLabelText("Home city")).toBeInTheDocument();
    expect(screen.getByText("Candidate travel windows")).toBeInTheDocument();
    expect(screen.getByLabelText("Europe destination map")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --filter @solo/web test -- --run src/app/page.test.tsx`

Expected: FAIL because the web app does not exist.

- [ ] **Step 3: Create web package and config**

Create `apps/web/package.json`:

```json
{
  "name": "@solo/web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "lint": "next lint",
    "test": "vitest --environment jsdom"
  },
  "dependencies": {
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.1.0",
    "@vitejs/plugin-react": "^4.3.4",
    "next": "^15.1.4",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "vitest": "^2.1.8"
  },
  "devDependencies": {
    "@types/node": "^22.10.5",
    "@types/react": "^19.0.2",
    "@types/react-dom": "^19.0.2",
    "eslint": "^9.17.0",
    "eslint-config-next": "^15.1.4",
    "jsdom": "^25.0.1",
    "typescript": "^5.7.2"
  }
}
```

Create `apps/web/next.config.ts`:

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
```

Create `apps/web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "es2022"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

Create `apps/web/vitest.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
  },
});
```

Create `apps/web/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 4: Create layout, styles, and page**

Create `apps/web/src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Solo",
  description: "Plan flexible long-weekend trips from your home city.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

Create `apps/web/src/app/globals.css`:

```css
:root {
  color: #18201d;
  background: #f7f5ef;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
}

main {
  min-height: 100vh;
  padding: 32px;
}

.shell {
  max-width: 1120px;
  margin: 0 auto;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
  gap: 32px;
  align-items: start;
}

.panel {
  border: 1px solid #d8d2c2;
  border-radius: 8px;
  background: #fffdf7;
  padding: 24px;
}

.stack {
  display: grid;
  gap: 16px;
}

label {
  display: grid;
  gap: 8px;
  font-weight: 700;
}

input,
select {
  min-height: 44px;
  border: 1px solid #c8c1b1;
  border-radius: 6px;
  padding: 10px 12px;
  font: inherit;
  background: white;
}

button {
  min-height: 44px;
  border: 0;
  border-radius: 6px;
  padding: 10px 14px;
  font: inherit;
  font-weight: 800;
  color: white;
  background: #24745a;
}

.window-list,
.recommendation-list {
  display: grid;
  gap: 12px;
  padding: 0;
  list-style: none;
}

.item {
  border: 1px solid #ded8c8;
  border-radius: 8px;
  padding: 14px;
  background: #ffffff;
}

@media (max-width: 820px) {
  main {
    padding: 20px;
  }

  .hero {
    grid-template-columns: 1fr;
  }
}
```

Create `apps/web/src/app/page.tsx` using the calendar-map workspace described in the Visual Baseline Update. The initial static page must include a left calendar panel, center map area, and right recommendation panel:

```tsx
const travelWindows = [
  { id: "may", label: "Spring bank holiday", dates: "23-25 May 2026" },
  { id: "august", label: "Summer bank holiday", dates: "29-31 Aug 2026" },
];

const recommendations = [
  { city: "Lisbon", country: "Portugal", why: "Warm, food-led, walkable, excellent for a long weekend." },
  { city: "Seville", country: "Spain", why: "Strong spring/autumn fit with history, food, and wandering time." },
  { city: "Porto", country: "Portugal", why: "Compact, atmospheric, and easy to enjoy without overplanning." },
];

export default function Page() {
  return (
    <main>
      <div className="shell hero">
        <section className="stack">
          <div>
            <h1>Solo</h1>
            <p>Long-weekend map planner</p>
          </div>

          <div className="panel stack">
            <label>
              Home city
              <input defaultValue="London" />
            </label>

            <div>
              <h2>Candidate travel windows</h2>
              <ul className="window-list">
                {travelWindows.map((window) => (
                  <li className="item" key={window.id}>
                    <strong>{window.label}</strong>
                    <div>{window.dates}</div>
                  </li>
                ))}
              </ul>
            </div>

            <label>
              Travel pace
              <select defaultValue="wandering">
                <option value="rushed">Rushed</option>
                <option value="balanced">Balanced</option>
                <option value="wandering">Wandering</option>
              </select>
            </label>

            <button type="button">Find destinations</button>
          </div>
        </section>

        <section className="map" aria-label="Europe destination map">
          <div className="pin home">London</div>
          <div className="pin">Lisbon 92</div>
          <div className="pin pin-alt">Seville 89</div>
          <div className="pin pin-gold">Porto 84</div>
        </section>

        <section className="panel">
          <h2>Recommended for your next windows</h2>
          <ul className="recommendation-list">
            {recommendations.map((item) => (
              <li className="item" key={item.city}>
                <strong>{item.city}, {item.country}</strong>
                <p>{item.why}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </main>
  );
}
```

- [ ] **Step 5: Run page test**

Run: `pnpm --filter @solo/web test -- --run src/app/page.test.tsx`

Expected: PASS.

- [ ] **Step 6: Commit web skeleton**

```bash
git add apps/web
git commit -m "feat: add Solo web shell"
```

---

## Task 9: Frontend Date Helpers And API Client

**Files:**
- Create: `apps/web/src/lib/types.ts`
- Create: `apps/web/src/lib/date-windows.ts`
- Create: `apps/web/src/lib/date-windows.test.ts`
- Create: `apps/web/src/lib/api.ts`

- [ ] **Step 1: Write failing date helper tests**

Create `apps/web/src/lib/date-windows.test.ts`:

```ts
import { durationDays, formatWindowLabel } from "./date-windows";

describe("date window helpers", () => {
  it("counts inclusive days", () => {
    expect(durationDays("2026-05-23", "2026-05-25")).toBe(3);
  });

  it("formats a readable window label", () => {
    expect(formatWindowLabel("2026-08-29", "2026-08-31")).toBe("29 Aug-31 Aug 2026");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm --filter @solo/web test -- --run src/lib/date-windows.test.ts`

Expected: FAIL because `date-windows.ts` does not exist.

- [ ] **Step 3: Implement shared frontend types and helpers**

Create `apps/web/src/lib/types.ts`:

```ts
export type Pace = "rushed" | "balanced" | "wandering";

export type TravelWindow = {
  id: string;
  start_date: string;
  end_date: string;
  label?: string | null;
  linked_holiday?: string | null;
  status?: "candidate" | "planned" | "archived";
};

export type PreferenceProfile = {
  pace: Pace;
  climate?: "cool" | "mild" | "warm" | "any";
  budget_sensitivity?: number;
  popularity?: "popular" | "underrated" | "mix";
  interests?: Record<string, number>;
};

export type RecommendationRequest = {
  home_city: string;
  travel_windows: TravelWindow[];
  preferences: PreferenceProfile;
  excluded_destination_ids: string[];
};

export type Destination = {
  id: string;
  city: string;
  country: string;
  tags: string[];
  climate_notes: string;
  caveats: string[];
};

export type Recommendation = {
  travel_window_id: string;
  destination: Destination;
  score: number;
  reasons: string[];
  caveats: string[];
};

export type RecommendationGroup = {
  travel_window: TravelWindow;
  recommendations: Recommendation[];
};
```

Create `apps/web/src/lib/date-windows.ts`:

```ts
const dayMs = 24 * 60 * 60 * 1000;

export function durationDays(startDate: string, endDate: string): number {
  const start = new Date(`${startDate}T00:00:00Z`);
  const end = new Date(`${endDate}T00:00:00Z`);
  return Math.floor((end.getTime() - start.getTime()) / dayMs) + 1;
}

export function formatWindowLabel(startDate: string, endDate: string): string {
  const start = new Date(`${startDate}T00:00:00Z`);
  const end = new Date(`${endDate}T00:00:00Z`);
  const month = new Intl.DateTimeFormat("en-GB", { month: "short", timeZone: "UTC" });
  const year = new Intl.DateTimeFormat("en-GB", { year: "numeric", timeZone: "UTC" });
  return `${start.getUTCDate()} ${month.format(start)}-${end.getUTCDate()} ${month.format(end)} ${year.format(end)}`;
}
```

Create `apps/web/src/lib/api.ts`:

```ts
import type { RecommendationGroup, RecommendationRequest } from "./types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function fetchRecommendations(request: RecommendationRequest): Promise<RecommendationGroup[]> {
  const response = await fetch(`${apiBaseUrl}/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Recommendation request failed with ${response.status}`);
  }

  return response.json();
}
```

- [ ] **Step 4: Run frontend helper tests**

Run: `pnpm --filter @solo/web test -- --run src/lib/date-windows.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit frontend helpers**

```bash
git add apps/web/src/lib
git commit -m "feat: add frontend travel window helpers"
```

---

## Task 10: Connect Calendar-Map UI To Recommendation API

**Files:**
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/page.test.tsx`

- [ ] **Step 1: Update page test for interactive UI**

Replace `apps/web/src/app/page.test.tsx` with:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import Page from "./page";

describe("Solo homepage", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => [
          {
            travel_window: { id: "may", start_date: "2026-05-23", end_date: "2026-05-25" },
            recommendations: [
              {
                travel_window_id: "may",
                destination: { id: "lisbon-pt", city: "Lisbon", country: "Portugal", tags: [], climate_notes: "", caveats: [] },
                score: 91,
                reasons: ["Matches your preference for warmer destinations."],
                caveats: []
              }
            ]
          }
        ],
      })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads recommendations from the API into the map workspace", async () => {
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(screen.getByText("Lisbon, Portugal")).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails against static page**

Run: `pnpm --filter @solo/web test -- --run src/app/page.test.tsx`

Expected: FAIL because the current page does not call `fetchRecommendations`.

- [ ] **Step 3: Implement client-side recommendation loading**

Replace `apps/web/src/app/page.tsx` with:

```tsx
"use client";

import { useState } from "react";
import { fetchRecommendations } from "@/lib/api";
import type { RecommendationGroup } from "@/lib/types";

const defaultWindows = [
  { id: "may", start_date: "2026-05-23", end_date: "2026-05-25", label: "Spring bank holiday" },
  { id: "august", start_date: "2026-08-29", end_date: "2026-08-31", label: "Summer bank holiday" },
];

export default function Page() {
  const [homeCity, setHomeCity] = useState("London");
  const [pace, setPace] = useState<"rushed" | "balanced" | "wandering">("wandering");
  const [groups, setGroups] = useState<RecommendationGroup[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");

  async function handleFindDestinations() {
    setStatus("loading");
    try {
      const results = await fetchRecommendations({
        home_city: homeCity,
        travel_windows: defaultWindows,
        preferences: {
          pace,
          climate: "warm",
          budget_sensitivity: 3,
          popularity: "mix",
          interests: { food: 5, history: 3, museums: 2, nature: 2, architecture: 4 },
        },
        excluded_destination_ids: [],
      });
      setGroups(results);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }

  return (
    <main>
      <div className="shell hero">
        <section className="stack">
          <div>
            <h1>Solo</h1>
            <p>Long-weekend map planner</p>
          </div>

          <div className="panel stack">
            <label>
              Home city
              <input value={homeCity} onChange={(event) => setHomeCity(event.target.value)} />
            </label>

            <div>
              <h2>Candidate travel windows</h2>
              <ul className="window-list">
                {defaultWindows.map((window) => (
                  <li className="item" key={window.id}>
                    <strong>{window.label}</strong>
                    <div>{window.start_date} to {window.end_date}</div>
                  </li>
                ))}
              </ul>
            </div>

            <label>
              Travel pace
              <select value={pace} onChange={(event) => setPace(event.target.value as typeof pace)}>
                <option value="rushed">Rushed</option>
                <option value="balanced">Balanced</option>
                <option value="wandering">Wandering</option>
              </select>
            </label>

            <button type="button" onClick={handleFindDestinations}>
              {status === "loading" ? "Finding..." : "Find destinations"}
            </button>
            {status === "error" ? <p role="alert">Could not load recommendations.</p> : null}
          </div>
        </section>

        <section className="map" aria-label="Europe destination map">
          <div className="pin home">{homeCity}</div>
          {groups.flatMap((group) =>
            group.recommendations.slice(0, 5).map((item, index) => (
              <button className="pin" type="button" key={`${group.travel_window.id}-${item.destination.id}`}>
                {item.destination.city} {item.score}
              </button>
            )),
          )}
        </section>

        <section className="panel">
          <h2>Recommended for your next windows</h2>
          {groups.length === 0 ? (
            <p>Choose your windows and preferences to compare destination ideas.</p>
          ) : (
            <div className="stack">
              {groups.map((group) => (
                <div key={group.travel_window.id}>
                  <h3>{group.travel_window.label ?? group.travel_window.id}</h3>
                  <ul className="recommendation-list">
                    {group.recommendations.map((item) => (
                      <li className="item" key={item.destination.id}>
                        <strong>{item.destination.city}, {item.destination.country}</strong>
                        <p>{item.reasons[0]}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
```

- [ ] **Step 4: Run page test**

Run: `pnpm --filter @solo/web test -- --run src/app/page.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit API-connected UI**

```bash
git add apps/web/src/app/page.tsx apps/web/src/app/page.test.tsx
git commit -m "feat: connect web shell to recommendations"
```

---

## Task 11: Shared Contracts Notes

**Files:**
- Create: `packages/shared/README.md`

- [ ] **Step 1: Create shared contract notes**

Create `packages/shared/README.md`:

```markdown
# Shared Contracts

This package is intentionally small. The backend owns runtime validation through Pydantic models in `apps/api/src/solo_api/models.py`. The frontend mirrors the request and response shapes in `apps/web/src/lib/types.ts`.

When API schemas stabilize, generate OpenAPI-derived TypeScript types here instead of hand-maintaining duplicate types.
```

- [ ] **Step 2: Commit shared package notes**

```bash
git add packages/shared/README.md
git commit -m "docs: document shared contract boundary"
```

---

## Task 12: Full Verification

**Files:**
- No source changes expected.

- [ ] **Step 1: Install dependencies**

Run: `pnpm install`

Expected: dependencies install and `pnpm-lock.yaml` is created.

- [ ] **Step 2: Install Python API dependencies**

Run: `cd apps/api && python -m pip install -e ".[dev]"`

Expected: FastAPI, pytest, and dev dependencies install.

- [ ] **Step 3: Run API tests**

Run: `pnpm test:api`

Expected: all API tests pass.

- [ ] **Step 4: Run frontend tests**

Run: `pnpm test:web -- --run`

Expected: all frontend tests pass.

- [ ] **Step 5: Run combined test command**

Run: `pnpm test`

Expected: API and frontend tests pass from the root.

- [ ] **Step 6: Commit lockfile and verification updates**

```bash
git add pnpm-lock.yaml
git commit -m "chore: lock workspace dependencies"
```

---

## Scope Notes For Later Plans

- Google SSO and durable persistence should be a separate plan after the local vertical slice works.
- Postgres migrations should be introduced with SQLAlchemy or SQLModel in the persistence plan.
- AI itinerary generation should replace the deterministic itinerary builder in a dedicated AI integration plan.
- Flight monitoring should remain a future plan with a background worker, provider abstraction, notification preferences, and provider-specific tests.

## Self-Review

- Spec coverage: this plan covers the monorepo, Next.js web app, FastAPI API, curated destination provider, bank-holiday provider, multiple travel windows, exclusions, grouped recommendations, and window-aware itineraries. Google SSO, Postgres persistence, live providers, and flight monitoring are acknowledged as separate later plans, matching the approved v1 staging.
- Placeholder scan: the plan contains concrete files, commands, code blocks, and expected results for each implementation task.
- Type consistency: backend `TravelWindow`, `PreferenceProfile`, `RecommendationRequest`, and `RecommendationGroup` names match the frontend mirrored types and the route examples.
