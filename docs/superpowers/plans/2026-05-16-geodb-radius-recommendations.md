# GeoDB Radius Recommendations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded Europe seed candidates with GeoDB-backed city discovery using population and radius filters, while keeping live recommendation scoring.

**Architecture:** The backend discovers candidate cities through GeoDB, caches candidate lists, then scores those cities with the existing live signal pipeline. The frontend sends radius and population filters with recommendation requests, draws the search radius on the map, and keeps score explanations inside a score tooltip.

**Tech Stack:** FastAPI, Pydantic, httpx, GeoDB Cities API, in-memory TTL cache, Next.js, MapLibre, Vitest, pytest.

---

### Task 1: Replace Seed Destination Source

**Files:**
- Create: `apps/api/src/solo_api/city_candidates.py`
- Delete: `apps/api/src/solo_api/destinations.py`
- Delete: `data/destinations/europe-seed.json`
- Test: `apps/api/tests/test_city_candidates.py`

- [x] Query GeoDB for city candidates with `minPopulation`, `radius`, `location`, and `namePrefix` where possible.
- [x] Cache candidate lists by center coordinates, radius, population, limit, region, and query.
- [x] For radii above GeoDB Basic native-radius limits, query European city candidates from GeoDB and apply exact local haversine filtering.

### Task 2: Simplify Destination Model

**Files:**
- Modify: `apps/api/src/solo_api/models.py`
- Modify: `apps/web/src/lib/types.ts`

- [x] Remove seed-only destination fields: `climate_notes`, `caveats`, `seasonal_strengths`, `tags`, `short_stay_score`, `solo_friendliness`, and `cost_level`.
- [x] Keep only live candidate fields needed for scoring and display: id, city, country, coordinates, timezone, region, country code, and population.

### Task 3: Update Recommendation Candidate Flow

**Files:**
- Modify: `apps/api/src/solo_api/recommendations.py`
- Modify: `apps/api/src/solo_api/main.py`
- Test: `apps/api/tests/test_recommendations.py`

- [x] Pass radius, population, query, and center coordinates into candidate search.
- [x] Score dynamic candidates with Open-Meteo, OSM/Overpass, Wikimedia/population, and static cost signals.
- [x] Preserve existing `/recommendations` grouping for the date-range flow.
- [x] Extend `/api/destinations/recommended` with `latitude`, `longitude`, `radiusKm`, and `minPopulation`.

### Task 4: Radius UI And Map Circle

**Files:**
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/destination-map.tsx`
- Modify: `apps/web/src/app/globals.css`
- Test: `apps/web/src/app/page.test.tsx`
- Test: `apps/web/src/app/destination-map.test.ts`

- [x] Add search radius and minimum population controls.
- [x] Send radius and population values in the recommendation payload.
- [x] Use API-provided destination coordinates instead of hardcoded city coordinates.
- [x] Draw a MapLibre radius circle and render a visible radius chip.

### Task 5: Score Breakdown Tooltip

**Files:**
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/globals.css`
- Test: `apps/web/src/app/page.test.tsx`

- [x] Keep total score visible as a compact number.
- [x] Show climate, attraction, popularity, and affordability scores in a hover/focus tooltip.
- [x] Avoid a separate always-visible score breakdown section.

### Exit Conditions

- [x] `europe-seed.json` and the old seed loader are deleted.
- [x] No app/data references remain to seed-only destination fields.
- [x] Recommendation candidates come from GeoDB-backed API calls with cache.
- [x] Radius and population filters are passed from the UI and used by backend candidate discovery.
- [x] Map displays a radius circle/chip for the active radius.
- [x] Score breakdown appears in the score tooltip.
- [x] API tests, Python lint, web tests, and web build pass.
- [x] Live smoke test returns a GeoDB candidate and proves candidate/signal cache reuse.
