# Live Recommendations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace seed-only recommendation scoring with cache-backed live destination signals.

**Architecture:** Keep seed destinations as candidates, add a focused live-signal enrichment module, and reuse it from both the existing POST `/recommendations` route and a new GET `/api/destinations/recommended` route. Provider failures return warnings and fallback scores instead of breaking search.

**Tech Stack:** FastAPI, Pydantic, httpx-backed providers, in-memory TTL cache, pytest, existing Next.js client contract.

---

### Task 1: Extend Recommendation Models

**Files:**
- Modify: `apps/api/src/solo_api/models.py`
- Modify: `apps/web/src/lib/types.ts`

- [x] Add score breakdown, warning, top attraction, summary, best-month, and estimated-budget fields to recommendations while keeping existing fields intact.

### Task 2: Add Cached Live Signals

**Files:**
- Create: `apps/api/src/solo_api/recommendation_signals.py`
- Test: `apps/api/tests/test_recommendations.py`

- [x] Add tests proving live signals are cached by destination/date key.
- [x] Add tests proving provider failures return warnings and fallback values.
- [x] Implement cached provider orchestration over Open-Meteo, Overpass, Wikimedia, and static cost data.

### Task 3: Replace Seed Scoring

**Files:**
- Modify: `apps/api/src/solo_api/recommendations.py`
- Test: `apps/api/tests/test_recommendations.py`

- [x] Add tests proving score is built from climate, attraction, popularity, and affordability parts.
- [x] Replace the old seed-only scorer with weighted live-signal scoring.
- [x] Preserve grouped recommendation response shape for the existing frontend.

### Task 4: Add Direct Recommended Destinations Endpoint

**Files:**
- Modify: `apps/api/src/solo_api/main.py`
- Modify: `apps/api/src/solo_api/models.py`
- Test: `apps/api/tests/test_recommendations.py`

- [x] Add GET `/api/destinations/recommended?month=&budget=&region=&q=` returning sorted destination results.
- [x] Include `travelScore`, `scoreBreakdown`, `bestMonthsToVisit`, `topAttractions`, `estimatedDailyBudget`, `summary`, and `warning`.

### Task 5: Frontend Compatibility

**Files:**
- Modify: `apps/web/src/lib/types.ts`
- Existing page tests: `apps/web/src/app/page.test.tsx`

- [x] Keep frontend recommendation loading unchanged except for optional new fields in types.
- [x] Verify the existing page flow still renders recommendations and map pins.

### Task 6: Verification

**Commands:**
- [x] `cd apps/api; python -m pytest tests/test_recommendations.py -v`
- [x] `cd apps/api; python -m pytest`
- [x] `corepack pnpm --filter @solo/web test -- --run`
- [x] `corepack pnpm --filter @solo/web build`
