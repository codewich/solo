# Rectangle Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit radius/rectangle destination search modes, persist the selected mode with saved travel-window searches, and restore saved rectangle searches in the UI.

**Architecture:** The backend request model accepts an explicit `search_mode` plus optional normalized rectangle bounds. Storage persists those values on `recommendation_searches`, candidate search dispatches to radius or bounds queries, and the frontend owns the mode/bounds state while `DestinationMap` owns map drawing interaction.

**Tech Stack:** FastAPI/Pydantic, psycopg/Postgres/Supabase, Next.js/React/TypeScript, MapLibre, shadcn-style controls.

---

### Task 1: Backend Models And Storage Shape

**Files:**
- Modify: `apps/api/src/solo_api/models.py`
- Modify: `apps/api/src/solo_api/storage.py`
- Create: `docs/supabase-rectangle-search.sql`
- Test: `apps/api/tests/test_models.py`
- Test: `apps/api/tests/test_storage.py`

- [ ] **Step 1: Add model tests**

Add tests that prove rectangle mode requires bounds, rejects inverted bounds, accepts valid bounds, and includes saved latest-search metadata.

- [ ] **Step 2: Add API model types**

Add `SearchBounds`, `SearchMode`, `search_mode`, and `search_bounds` to `RecommendationSearchCreateRequest` and `RecommendationSearchSummary`. Use validation so rectangle mode requires valid bounds and radius mode clears bounds.

- [ ] **Step 3: Add DB schema SQL**

Create `docs/supabase-rectangle-search.sql` with `alter table public.recommendation_searches add column if not exists search_mode text not null default 'radius'`, `add column if not exists search_bounds jsonb`, and a check constraint for `search_mode in ('radius', 'rectangle')`.

- [ ] **Step 4: Update storage persistence**

Pass `search_mode` and normalized `search_bounds` into `create_or_replace_recommendation_search`, compare them in replacement logic, persist them in the upsert, return them from `get_recommendation_search`, and include them in `list_travel_windows`.

- [ ] **Step 5: Run backend model/storage tests**

Run `./.venv/bin/python -m pytest apps/api/tests/test_models.py apps/api/tests/test_storage.py -q`.

### Task 2: Rectangle Candidate Search

**Files:**
- Modify: `apps/api/src/solo_api/city_candidates.py`
- Modify: `apps/api/src/solo_api/storage.py`
- Modify: `apps/api/src/solo_api/recommendation_searches.py`
- Test: `apps/api/tests/test_city_candidates.py`
- Test: `apps/api/tests/test_recommendations.py`

- [ ] **Step 1: Add city-candidate tests**

Add tests for a new rectangle city search helper that passes bounds to storage and returns empty results for an empty imported catalog query.

- [ ] **Step 2: Add bounded storage query**

Add `find_city_candidates_in_bounds(west, south, east, north, min_population, limit, region, query)` using latitude/longitude comparisons, population filtering, optional country/region/query filtering, population-desc ordering, and limit.

- [ ] **Step 3: Add search helper**

Add `search_city_candidates_in_bounds` beside the radius helper and keep the existing radius helper unchanged.

- [ ] **Step 4: Dispatch by search mode**

Extend `MemorySearch` with `search_mode` and `search_bounds`. In `list_recommendation_search_cities`, call the bounded helper for rectangle mode and the radius helper for radius mode.

- [ ] **Step 5: Run backend recommendation tests**

Run `./.venv/bin/python -m pytest apps/api/tests/test_city_candidates.py apps/api/tests/test_recommendations.py -q`.

### Task 3: Frontend Types And Search State

**Files:**
- Modify: `apps/web/src/lib/types.ts`
- Modify: `apps/web/src/app/page.tsx`
- Test: `apps/web/src/app/page.test.tsx`

- [ ] **Step 1: Add frontend types**

Add `SearchMode` and `SearchBounds` types. Extend `TravelWindow.latest_search` and `RecommendationSearchCreateRequest` with `search_mode` and `search_bounds`.

- [ ] **Step 2: Add page state**

Add `searchMode` and `searchBounds` state. Restore them from `window.latest_search` in `handleTravelWindowSelect`. Clear or preserve values according to the approved design: radius value persists, rectangle bounds persist until cleared.

- [ ] **Step 3: Send explicit search payload**

Update `handleFindDestinations` to include `search_mode` and `search_bounds` only for rectangle mode. Block rectangle searches without bounds with the existing persistent sonner error.

- [ ] **Step 4: Add UI tests**

Cover payloads for radius and rectangle mode, disabled search without bounds, and saved rectangle metadata restoration.

### Task 4: Rectangle Controls And Map Drawing

**Files:**
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/destination-map.tsx`
- Test: `apps/web/src/app/destination-map.test.ts`
- Test: `apps/web/src/app/page.test.tsx`

- [ ] **Step 1: Add explicit mode controls**

Use the existing shadcn button/card styling to render a two-option segmented control in `Search area`. Hide the radius slider in rectangle mode and show `Draw rectangle`, `Redraw`, `Clear`, and bounds summary instead.

- [ ] **Step 2: Extend `DestinationMap` props**

Add `searchMode`, `searchBounds`, `isDrawingRectangle`, `onSearchBoundsChange`, and `onDrawingRectangleChange`.

- [ ] **Step 3: Draw rectangle overlay**

Add a `search-rectangle` GeoJSON source/layers and remove or hide `search-radius` when rectangle mode is active. Keep only one search shape visible.

- [ ] **Step 4: Add drag interaction**

When drawing mode is active, disable map panning and use pointer down/move/up to compute bounds from `map.unproject`. Normalize the bounds and emit them to the page. Re-enable panning after completion/cancel.

- [ ] **Step 5: Update tests**

Assert radius chip text in radius mode, rectangle chip text in rectangle mode, and that the page hides radius controls while rectangle controls are shown.

### Task 5: Verification

**Files:**
- No production changes unless verification reveals defects.

- [ ] **Step 1: Run API tests**

Run `./.venv/bin/python -m pytest apps/api/tests/test_models.py apps/api/tests/test_storage.py apps/api/tests/test_city_candidates.py apps/api/tests/test_recommendations.py -q`.

- [ ] **Step 2: Run web tests**

Run `pnpm --filter @solo/web test -- --run`.

- [ ] **Step 3: Run lint and build**

Run `pnpm --filter @solo/web lint` and `pnpm --filter @solo/web build`.

- [ ] **Step 4: Final acceptance check**

Confirm the implementation satisfies every acceptance condition from `docs/superpowers/specs/2026-05-21-rectangle-search-design.md`.
