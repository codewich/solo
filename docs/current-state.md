# Solo Current State

Last updated: 2026-05-15

This document is a handoff for the next agent. It describes the code that is currently on `master`, what works, how to run it, and where the next likely changes should land.

## Repository Shape

Solo is a fullstack monorepo:

- `apps/web`: Next.js, React, and TypeScript frontend.
- `apps/api`: FastAPI and Pydantic backend.
- `data/destinations`: curated seed destination data.
- `packages/shared`: notes for future generated shared contracts.
- `docs/roadmap.md`: product roadmap and next milestone direction.
- `docs/superpowers/specs/2026-05-14-solo-long-weekend-travel-design.md`: original product design.
- `docs/superpowers/plans/2026-05-14-solo-mvp-foundation.md`: original implementation plan.

The active branch is `master`. The Solo app was developed in the `solo-mvp` worktree, then moved into the main checkout with commit `c480999 feat: move Solo app into main`.

## Local Commands

From the repo root:

```bash
corepack pnpm install
python -m venv apps/api/.venv
apps/api/.venv/Scripts/python.exe -m pip install -e "apps/api[dev]"
corepack pnpm dev:api
corepack pnpm dev:web
corepack pnpm test
```

Local ports:

- Web: `http://localhost:3000`
- API: `http://localhost:45655`

The API was moved to port `45655` because port `8000` hit a Windows socket permission error on this machine.

## Verification State

The latest verification from `C:\Users\Michael\projects\solo`:

```bash
corepack pnpm test
```

Result:

- Frontend: 7 tests passed.
- Backend: 14 tests passed.

Dependencies are intentionally not tracked. `node_modules`, `.venv`, and `.next` are ignored and can be rebuilt.

## Backend State

Entry point: `apps/api/src/solo_api/main.py`

Implemented routes:

- `GET /health`
- `GET /holidays`
- `POST /recommendations`
- `POST /itineraries`

Core backend files:

- `models.py`: Pydantic models for `TravelWindow`, `PreferenceProfile`, `Destination`, `RecommendationRequest`, `Recommendation`, and `RecommendationGroup`.
- `destinations.py`: loads curated destinations from `data/destinations/europe-seed.json`.
- `holidays.py`: static UK 2026 bank holidays.
- `recommendations.py`: deterministic recommendation scoring and filtering.
- `itineraries.py`: deterministic itinerary draft generation.

Current domain model notes:

- `TravelWindow` includes `id`, `start_date`, `end_date`, `label`, `linked_holiday`, `status`, and `notes`.
- `TravelWindow.duration_days` is inclusive.
- Invalid ranges where `end_date < start_date` are rejected.
- The recommendation request supports multiple travel windows and excluded destination IDs.

Current backend limitations:

- No database.
- No authentication.
- No live holiday, weather, event, map, city-search, AI, or flight provider.
- Seeded destination data is deterministic and small.
- Itinerary generation is deterministic, not AI-backed.

## Frontend State

Main page: `apps/web/src/app/page.tsx`

The app currently renders a single planning workspace:

- Top bar with app name and home city.
- Left panel for home city, travel pace, calendar, candidate travel windows, preference lens, and search button.
- Center CSS-positioned Europe-style mock map.
- Right panel with best matches for the selected travel window.

Implemented interactions:

- Home city input updates local state.
- Travel pace selector updates local state.
- May 2026 calendar lets the user create a draft date range by clicking start and end dates.
- `Add range` adds the draft range to the candidate range list.
- Candidate ranges can be selected, renamed, archived, and removed.
- Selected range drives the active recommendation group after recommendations are loaded.
- `Find destinations` calls the FastAPI `/recommendations` endpoint.
- If the API call fails, the page shows `Could not load recommendations.`

Frontend support files:

- `apps/web/src/lib/api.ts`: browser API client. Fallback API URL is `http://localhost:45655`.
- `apps/web/src/lib/types.ts`: frontend mirrors of API request/response shapes.
- `apps/web/src/lib/date-windows.ts`: date duration and display-label helpers.
- `apps/web/src/app/globals.css`: all current styling, including range-list UI and mock map pins.

Current frontend limitations:

- Calendar only shows May 2026.
- Calendar is not a full multi-month picker.
- Range edits currently support label changes, archive toggle, and remove, but not changing start/end dates from the list.
- Range state is local only and disappears on refresh.
- Home city is plain text, not autocomplete.
- Map is CSS-positioned, not a real map.
- Destination marker clicks do not open a real detail drawer yet.
- Recommendation cards show static tags like `4 days`, `solo-friendly`, and `walkable`.

## Tests

Frontend tests:

- `apps/web/src/app/page.test.tsx`
  - renders the workspace.
  - loads API-backed recommendations.
  - keeps draft calendar selection separate from saved ranges.
  - uses selected travel window for recommendation emphasis.
  - adds, renames, archives, and removes ranges.
- `apps/web/src/lib/date-windows.test.ts`
  - inclusive date duration.
  - readable date label formatting.

Backend tests:

- `test_health.py`
- `test_models.py`
- `test_destinations.py`
- `test_holidays.py`
- `test_recommendations.py`
- `test_itineraries.py`

## Product Direction

The next milestone should follow `docs/roadmap.md`, especially Phase 1:

1. Promote the current local range model into a cleaner frontend/API range model.
2. Improve the range list so ranges can be edited more completely.
3. Wire selected range state through recommendations, map pins, and itinerary preview.
4. Replace the CSS map with Leaflet or MapLibre.
5. Add city autocomplete for home city selection.
6. Add local persistence, then Postgres and Google SSO.

The user specifically wants:

- service-backed autocomplete for home city selection.
- a real map in the center of the app.
- a calendar-plus-range-list workflow where users select dates, add ranges, edit the range list, select a range, and see recommendations and plans for that range.

## Recommended Next Engineering Move

Do not start by adding providers. First split the large `apps/web/src/app/page.tsx` into focused pieces:

- calendar/range draft logic.
- candidate range list.
- map surface.
- recommendation panel.
- API request assembly.

Then add tests around those units before replacing the mock map or adding city autocomplete. This will make the real-map and provider work much easier to land without turning the page file into the whole app.
