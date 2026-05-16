# Next Step Goals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Solo's date ranges drive pacing and map visibility, improve responsive styling, lock home-city editing behind an edit affordance with geocoding autocomplete, and add destination intelligence from weather, POI, hotel, and cost data.

**Architecture:** Keep the existing Next.js page as the user workflow shell, but extract small UI helpers and API functions so each behavior can be tested independently. Add FastAPI service modules for Open-Meteo, Overpass, Wikimedia, Amadeus, and cost-of-living normalization, with outbound HTTP mocked in tests and short-lived in-memory caches for expensive or rate-limited calls.

**Tech Stack:** Next.js 15, React 19, Vitest, Testing Library, MapLibre, Tailwind CSS utilities with shadcn/ui-style component primitives, FastAPI, Pydantic v2, pytest, httpx.

---

## External API Notes

- Open-Meteo historical weather endpoint accepts WGS84 `latitude` and `longitude`, supports hourly/daily weather variables, and provides historical records back to 1940. Use `https://archive-api.open-meteo.com/v1/archive` for climate summaries and `https://geocoding-api.open-meteo.com/v1/search` for city autocomplete.
- Overpass API accepts Overpass QL at `https://overpass-api.de/api/interpreter`; bound each query to a destination radius to avoid large downloads.
- Wikimedia APIs provide open access to Wikipedia and sibling project content. Use REST page summaries for concise destination descriptions.
- Amadeus hotel APIs use OAuth and hotel list/search endpoints. Keep credentials in environment variables, cache price summaries, and return an unavailable state when credentials are absent.

## File Structure

- Modify `apps/web/package.json`: add Tailwind, shadcn/ui utility dependencies, and lucide icons.
- Create `apps/web/postcss.config.mjs`: enable Tailwind processing for Next.
- Modify `apps/web/src/app/globals.css`: import Tailwind, define design tokens, responsive layout rules, animation tokens, and component classes.
- Modify `apps/web/src/lib/types.ts`: add home location, geocoding, and destination intelligence frontend types.
- Modify `apps/web/src/lib/api.ts`: add geocoding autocomplete and destination intelligence fetchers.
- Create `apps/web/src/lib/travel-pacing.ts`: calculate inferred pace from date-range duration.
- Create `apps/web/src/lib/travel-pacing.test.ts`: unit-test pace calculation boundaries.
- Modify `apps/web/src/app/destination-map.tsx`: accept home coordinates, show home pin in red, and hide destination pins until a saved range is selected.
- Modify `apps/web/src/app/page.tsx`: clear saved draft date highlights, add an Add Range cancel action, paginate long range lists, tie pace to selected date range, lock/edit home city, autocomplete and geocode home city, fetch destination intelligence.
- Modify `apps/web/src/app/page.test.tsx`: cover clearing saved draft highlights, canceling draft range selection, pagination, inferred pace, home-city editing, autocomplete/geocoding, red home pin behavior, and destination intelligence rendering.
- Modify `apps/api/pyproject.toml`: add `httpx`.
- Modify `apps/api/src/solo_api/models.py`: add destination intelligence request/response models and coordinate/cost models.
- Create `apps/api/src/solo_api/http.py`: shared timeout-based HTTP client factory.
- Create `apps/api/src/solo_api/cache.py`: small TTL cache for destination intelligence and provider responses.
- Create `apps/api/src/solo_api/geocoding.py`: Open-Meteo city autocomplete and coordinate normalization.
- Create `apps/api/src/solo_api/weather.py`: Open-Meteo climate summary provider.
- Create `apps/api/src/solo_api/attractions.py`: Overpass POI and Wikimedia summary provider.
- Create `apps/api/src/solo_api/hotels.py`: Amadeus OAuth, hotel search, and median nightly price provider.
- Create `apps/api/src/solo_api/cost_of_living.py`: cost-of-living provider interface plus static starter provider.
- Create `apps/api/src/solo_api/destination_intelligence.py`: orchestrate normalized providers into one response.
- Modify `apps/api/src/solo_api/main.py`: add `/geocode/cities` and `/destination-intelligence` endpoints.
- Create `apps/api/tests/test_geocoding.py`: mocked Open-Meteo geocoding behavior.
- Create `apps/api/tests/test_destination_intelligence.py`: mocked provider aggregation, caching, and no-Amadeus fallback tests.
- Modify `README.md`: document new env vars and local development expectations.

---

### Task 1: Add Frontend Styling Foundation

**Files:**
- Modify: `apps/web/package.json`
- Create: `apps/web/postcss.config.mjs`
- Modify: `apps/web/src/app/globals.css`

- [ ] **Step 1: Add styling dependencies**

Run:

```powershell
corepack pnpm --filter @solo/web add tailwindcss @tailwindcss/postcss class-variance-authority clsx tailwind-merge lucide-react
```

Expected: `apps/web/package.json` includes the new dependencies and `pnpm-lock.yaml` updates.

- [ ] **Step 2: Create PostCSS config**

Create `apps/web/postcss.config.mjs`:

```js
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
```

- [ ] **Step 3: Replace global CSS with responsive tokens and component classes**

In `apps/web/src/app/globals.css`, keep the existing class names used by `page.tsx`, but rewrite the file around fluid spacing, larger readable type, focus states, and subtle transitions. Start the file with:

```css
@import "tailwindcss";

:root {
  color: #17211d;
  background: #f7f4ec;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
  --surface: #fffdf8;
  --surface-soft: #fbf8ef;
  --border: #d8d0bf;
  --text-muted: #5f6b64;
  --accent: #24745a;
  --accent-strong: #14513f;
  --danger: #a3362a;
  --home-pin: #d33b2f;
  --shadow-soft: 0 14px 34px rgba(31, 59, 49, 0.14);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
}

main {
  min-height: 100vh;
}

button,
input,
select {
  font: inherit;
}

button {
  transition:
    background 160ms ease,
    border-color 160ms ease,
    color 160ms ease,
    transform 160ms ease;
}

button:hover:not(:disabled) {
  transform: translateY(-1px);
}

button:focus-visible,
input:focus-visible,
select:focus-visible {
  outline: 3px solid rgba(36, 116, 90, 0.28);
  outline-offset: 2px;
}
```

Then update these existing selectors with responsive values:

```css
.topbar {
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: clamp(12px, 2vw, 22px);
  padding: clamp(14px, 2vw, 22px);
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

.workspace {
  display: grid;
  grid-template-columns: minmax(320px, 380px) minmax(420px, 1fr) minmax(340px, 400px);
  height: calc(100vh - 72px);
}

.panel {
  min-width: 0;
  padding: clamp(16px, 2vw, 22px);
  border-right: 1px solid var(--border);
  background: var(--surface-soft);
  overflow: auto;
}

.card {
  border: 1px solid #ddd5c3;
  border-radius: 8px;
  padding: clamp(12px, 1.5vw, 16px);
  background: white;
  box-shadow: 0 1px 0 rgba(31, 59, 49, 0.04);
}

.muted {
  color: var(--text-muted);
  font-size: clamp(0.875rem, 0.84rem + 0.16vw, 0.95rem);
  line-height: 1.5;
}

.pill {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  border: 1px solid #d3cbb9;
  border-radius: 999px;
  padding: 5px 10px;
  color: #4f5b54;
  background: var(--surface);
  font-size: 0.78rem;
  font-weight: 800;
  white-space: nowrap;
}

.range-list {
  display: grid;
  gap: 8px;
  max-height: min(430px, 48vh);
  overflow: auto;
  padding-right: 2px;
}

.range-button {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  border: 1px solid #ddd5c3;
  border-radius: 8px;
  padding: 11px;
  color: #17211d;
  background: var(--surface);
  text-align: left;
  cursor: pointer;
}

.range-button.active {
  border-color: var(--accent);
  background: #e4f2eb;
  box-shadow: inset 3px 0 0 var(--accent);
}

.primary-button {
  border: 0;
  border-radius: 6px;
  padding: 10px 13px;
  color: white;
  background: var(--accent);
  font-weight: 900;
}

.secondary-button {
  border: 1px solid #cfc6b1;
  border-radius: 6px;
  padding: 8px 10px;
  color: #24342e;
  background: var(--surface);
  font-size: 0.82rem;
  font-weight: 900;
  white-space: nowrap;
}

input,
select {
  min-height: 44px;
  border: 1px solid #cfc6b1;
  border-radius: 6px;
  padding: 10px 12px;
  background: white;
}

.home-city-control {
  display: grid;
  gap: 8px;
}

.home-city-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 38px;
  gap: 8px;
  align-items: end;
}

.autocomplete-list {
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 6px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: white;
  list-style: none;
  box-shadow: var(--shadow-soft);
}

.autocomplete-option {
  width: 100%;
  border: 0;
  border-radius: 6px;
  padding: 9px 10px;
  background: transparent;
  color: #17211d;
  text-align: left;
}

.autocomplete-option:hover,
.autocomplete-option:focus-visible {
  background: #e4f2eb;
}

.map-chip-home {
  background: var(--home-pin);
}

.map-chip.is-hidden {
  display: none;
}

.destination-intelligence {
  display: grid;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #ece4d2;
}

.pagination-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

@media (max-width: 1180px) {
  .workspace {
    grid-template-columns: minmax(320px, 360px) 1fr;
    height: auto;
  }

  .right-panel {
    grid-column: 1 / -1;
    border-left: 0;
    border-top: 1px solid var(--border);
  }

  .map {
    min-height: 560px;
  }
}

@media (max-width: 760px) {
  .topbar {
    align-items: start;
    flex-direction: column;
  }

  .brand {
    align-items: start;
    flex-direction: column;
    gap: 4px;
  }

  .workspace {
    grid-template-columns: 1fr;
  }

  .panel {
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }

  .row {
    align-items: stretch;
    flex-direction: column;
  }

  .map {
    min-height: 480px;
  }
}
```

- [ ] **Step 4: Run frontend tests**

Run:

```powershell
corepack pnpm --filter @solo/web test -- --run
```

Expected: Existing tests still pass before behavior changes.

- [ ] **Step 5: Commit**

```powershell
git add apps/web/package.json apps/web/postcss.config.mjs apps/web/src/app/globals.css pnpm-lock.yaml
git commit -m "style: add responsive styling foundation"
```

---

### Task 2: Infer Pace From Selected Date Range

**Files:**
- Create: `apps/web/src/lib/travel-pacing.ts`
- Create: `apps/web/src/lib/travel-pacing.test.ts`
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/page.test.tsx`

- [ ] **Step 1: Write the failing unit tests**

Create `apps/web/src/lib/travel-pacing.test.ts`:

```ts
import { inferPaceFromRange } from "./travel-pacing";

describe("inferPaceFromRange", () => {
  it("uses rushed pace for short windows", () => {
    expect(inferPaceFromRange({ start_date: "2026-05-22", end_date: "2026-05-23" })).toBe(
      "rushed",
    );
  });

  it("uses balanced pace for three or four day windows", () => {
    expect(inferPaceFromRange({ start_date: "2026-05-22", end_date: "2026-05-25" })).toBe(
      "balanced",
    );
  });

  it("uses wandering pace for longer windows", () => {
    expect(inferPaceFromRange({ start_date: "2026-12-24", end_date: "2026-12-30" })).toBe(
      "wandering",
    );
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
corepack pnpm --filter @solo/web test -- --run src/lib/travel-pacing.test.ts
```

Expected: FAIL because `apps/web/src/lib/travel-pacing.ts` does not exist.

- [ ] **Step 3: Implement pace inference**

Create `apps/web/src/lib/travel-pacing.ts`:

```ts
import type { Pace } from "./types";

type DateRange = {
  start_date: string;
  end_date: string;
};

function utcDayNumber(value: string): number {
  return Date.parse(`${value}T00:00:00Z`) / 86_400_000;
}

export function durationDays(range: DateRange): number {
  return Math.max(1, Math.round(utcDayNumber(range.end_date) - utcDayNumber(range.start_date)) + 1);
}

export function inferPaceFromRange(range: DateRange): Pace {
  const days = durationDays(range);

  if (days <= 2) {
    return "rushed";
  }

  if (days <= 4) {
    return "balanced";
  }

  return "wandering";
}
```

- [ ] **Step 4: Connect page state to inferred pace**

In `apps/web/src/app/page.tsx`:

1. Replace the manual pace state:

```ts
const [pace, setPace] = useState<"rushed" | "balanced" | "wandering">("wandering");
```

with:

```ts
import { inferPaceFromRange } from "@/lib/travel-pacing";

const pace = inferPaceFromRange(selectedTravelWindow);
```

Move the `pace` declaration below `selectedTravelWindow`.

2. Remove the `<label>` block containing `Travel pace` and its `<select>`.

3. Keep the preference lens pills, but make the pace pill read the inferred pace:

```tsx
<span className="pill">{pace[0].toUpperCase() + pace.slice(1)} pace</span>
```

- [ ] **Step 5: Add page test for pace changing with range duration**

Add this test to `apps/web/src/app/page.test.tsx`:

```tsx
it("infers travel pace from the selected date range", () => {
  render(<Page />);

  expect(screen.getByText("Balanced pace")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Add range" }));
  fireEvent.click(screen.getByRole("button", { name: "20 May 2026" }));
  fireEvent.click(screen.getByRole("button", { name: "27 May 2026" }));
  fireEvent.click(screen.getByRole("button", { name: "Save range" }));

  expect(screen.getByText("Wandering pace")).toBeInTheDocument();
  expect(screen.queryByLabelText("Travel pace")).not.toBeInTheDocument();
});
```

- [ ] **Step 6: Run frontend tests**

Run:

```powershell
corepack pnpm --filter @solo/web test -- --run src/lib/travel-pacing.test.ts src/app/page.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add apps/web/src/lib/travel-pacing.ts apps/web/src/lib/travel-pacing.test.ts apps/web/src/app/page.tsx apps/web/src/app/page.test.tsx
git commit -m "feat: infer travel pace from date ranges"
```

---

### Task 3: Clear Saved Range Highlight, Add Cancel, And Paginate Long Range Lists

**Files:**
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/page.test.tsx`

- [ ] **Step 1: Add failing page tests**

Add these tests to `apps/web/src/app/page.test.tsx`:

```tsx
it("clears the draft date highlight after a range is saved", () => {
  render(<Page />);

  fireEvent.click(screen.getByRole("button", { name: "Add range" }));
  expect(screen.getByLabelText("May 2026 calendar")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "20 May 2026" }));
  fireEvent.click(screen.getByRole("button", { name: "26 May 2026" }));
  fireEvent.click(screen.getByRole("button", { name: "Save range" }));

  expect(screen.getByLabelText("May 2026 calendar")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Add range" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "20 May 2026" })).not.toHaveClass("selected");
  expect(screen.getByRole("button", { name: "26 May 2026" })).not.toHaveClass("selected");
});

it("lets the user cancel adding a range", () => {
  render(<Page />);

  fireEvent.click(screen.getByRole("button", { name: "Add range" }));
  fireEvent.click(screen.getByRole("button", { name: "20 May 2026" }));

  expect(screen.getByText("Draft range: 20 May-20 May 2026")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "20 May 2026" })).toHaveClass("selected");

  fireEvent.click(screen.getByRole("button", { name: "Cancel range" }));

  expect(screen.queryByText(/Draft range:/)).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Add range" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "20 May 2026" })).not.toHaveClass("selected");
});

it("paginates candidate ranges when the list grows", () => {
  render(<Page />);

  for (let index = 0; index < 7; index += 1) {
    fireEvent.click(screen.getByRole("button", { name: "Add range" }));
    fireEvent.click(screen.getByRole("button", { name: `${10 + index} May 2026` }));
    fireEvent.click(screen.getByRole("button", { name: `${11 + index} May 2026` }));
    fireEvent.click(screen.getByRole("button", { name: "Save range" }));
  }

  expect(screen.getByText("Page 1 of 2")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Next ranges" })).toBeEnabled();
  expect(screen.queryByRole("button", { name: /Select 16 May-17 May 2026/ })).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Next ranges" }));

  expect(screen.getByText("Page 2 of 2")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Select 16 May-17 May 2026/ })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
corepack pnpm --filter @solo/web test -- --run src/app/page.test.tsx
```

Expected: FAIL because the saved date range remains highlighted, there is no cancel action, and range pagination controls do not exist.

- [ ] **Step 3: Add pagination state and derived list**

In `apps/web/src/app/page.tsx`, add constants near the top:

```ts
const rangePageSize = 6;
```

Add page state:

```ts
const [rangePageIndex, setRangePageIndex] = useState(0);
```

Add derived values after `selectedTravelWindow`:

```ts
const rangePageCount = Math.max(1, Math.ceil(travelWindows.length / rangePageSize));
const visibleTravelWindows = travelWindows.slice(
  rangePageIndex * rangePageSize,
  rangePageIndex * rangePageSize + rangePageSize,
);
```

- [ ] **Step 4: Reset or clamp pagination when ranges change**

Change the React import at the top of `apps/web/src/app/page.tsx`:

```ts
import { useEffect, useState } from "react";
```

After the derived range values, add:

```ts
useEffect(() => {
  setRangePageIndex((currentPage) => Math.min(currentPage, rangePageCount - 1));
}, [rangePageCount]);
```

When saving a new range, before clearing draft state:

```ts
setRangePageIndex(Math.floor(travelWindows.length / rangePageSize));
```

When removing a range, after `setTravelWindows(nextWindows)`:

```ts
setRangePageIndex((currentPage) =>
  Math.min(currentPage, Math.max(0, Math.ceil(nextWindows.length / rangePageSize) - 1)),
);
```

- [ ] **Step 5: Clear date range highlight when there is no active draft**

In `apps/web/src/app/page.tsx`, change:

```ts
const visibleCalendarRange = draftRange ?? selectedTravelWindow;
```

to:

```ts
const visibleCalendarRange = draftRange;
```

Then change the day selection calculation from:

```ts
const isSelected = isWithinRange(
  isoDate,
  visibleCalendarRange.start_date,
  visibleCalendarRange.end_date,
);
```

to:

```ts
const isSelected =
  visibleCalendarRange !== null &&
  isWithinRange(isoDate, visibleCalendarRange.start_date, visibleCalendarRange.end_date);
```

Keep the calendar visible at all times. The selected range should appear only while the user is actively drafting a new range; once the range is saved and `draftRange` returns to `null`, no date-range highlight should remain on the calendar.

- [ ] **Step 6: Add a cancel action for range drafting**

In `apps/web/src/app/page.tsx`, add:

```ts
function handleCancelRangeDraft() {
  setIsAddingRange(false);
  setDraftAnchorDate(null);
  setDraftRange(null);
  setIsDraftComplete(false);
}
```

Render the range action buttons as a small button group:

```tsx
<div className="range-create-actions">
  {isAddingRange ? (
    <button className="secondary-button" type="button" onClick={handleCancelRangeDraft}>
      Cancel range
    </button>
  ) : null}
  <button
    className="secondary-button"
    type="button"
    disabled={isAddingRange && !isDraftComplete}
    onClick={handleRangeButtonClick}
  >
    {isAddingRange ? "Save range" : "Add range"}
  </button>
</div>
```

Add `.range-create-actions` to `apps/web/src/app/globals.css` if Task 1 has not already added it:

```css
.range-create-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
}
```

- [ ] **Step 7: Render the paginated range list**

Change:

```tsx
{travelWindows.map((window) => {
```

to:

```tsx
{visibleTravelWindows.map((window) => {
```

Below the range list, render:

```tsx
{rangePageCount > 1 ? (
  <div className="pagination-controls" aria-label="Range pagination">
    <button
      className="secondary-button"
      type="button"
      disabled={rangePageIndex === 0}
      onClick={() => setRangePageIndex((currentPage) => Math.max(0, currentPage - 1))}
    >
      Previous ranges
    </button>
    <span className="muted">
      Page {rangePageIndex + 1} of {rangePageCount}
    </span>
    <button
      className="secondary-button"
      type="button"
      disabled={rangePageIndex === rangePageCount - 1}
      onClick={() =>
        setRangePageIndex((currentPage) => Math.min(rangePageCount - 1, currentPage + 1))
      }
    >
      Next ranges
    </button>
  </div>
) : null}
```

- [ ] **Step 8: Run tests**

Run:

```powershell
corepack pnpm --filter @solo/web test -- --run src/app/page.test.tsx
```

Expected: PASS.

- [ ] **Step 9: Commit**

```powershell
git add apps/web/src/app/page.tsx apps/web/src/app/page.test.tsx
git commit -m "feat: refine range drafting controls"
```

---

### Task 4: Add Backend Geocoding Autocomplete

**Files:**
- Modify: `apps/api/pyproject.toml`
- Create: `apps/api/src/solo_api/http.py`
- Create: `apps/api/src/solo_api/geocoding.py`
- Modify: `apps/api/src/solo_api/models.py`
- Modify: `apps/api/src/solo_api/main.py`
- Create: `apps/api/tests/test_geocoding.py`

- [ ] **Step 1: Add httpx dependency**

In `apps/api/pyproject.toml`, add `httpx` to dependencies:

```toml
dependencies = [
  "fastapi>=0.115.0",
  "httpx>=0.28.0",
  "pydantic>=2.10.0",
  "uvicorn[standard]>=0.34.0"
]
```

- [ ] **Step 2: Write failing geocoding tests**

Create `apps/api/tests/test_geocoding.py`:

```py
from fastapi.testclient import TestClient

from solo_api.main import app


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_city_geocoding_returns_normalized_suggestions(monkeypatch):
    calls = []

    def fake_get(url: str, params: dict):
        calls.append((url, params))
        return FakeResponse(
            {
                "results": [
                    {
                        "id": 2643743,
                        "name": "London",
                        "country": "United Kingdom",
                        "admin1": "England",
                        "latitude": 51.5085,
                        "longitude": -0.1257,
                        "timezone": "Europe/London",
                    }
                ]
            }
        )

    monkeypatch.setattr("solo_api.geocoding.httpx.get", fake_get)

    response = TestClient(app).get("/geocode/cities", params={"query": "London"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "2643743",
            "name": "London",
            "country": "United Kingdom",
            "admin1": "England",
            "latitude": 51.5085,
            "longitude": -0.1257,
            "timezone": "Europe/London",
        }
    ]
    assert calls[0][0] == "https://geocoding-api.open-meteo.com/v1/search"
    assert calls[0][1]["name"] == "London"


def test_city_geocoding_rejects_short_queries():
    response = TestClient(app).get("/geocode/cities", params={"query": "L"})

    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```powershell
cd apps/api; .venv\Scripts\python.exe -m pytest tests/test_geocoding.py -o cache_dir=C:\tmp\solo-pytest-cache
```

Expected: FAIL because `/geocode/cities` is not defined.

- [ ] **Step 4: Add shared HTTP constants**

Create `apps/api/src/solo_api/http.py`:

```py
import httpx

DEFAULT_TIMEOUT = httpx.Timeout(8.0, connect=4.0)
USER_AGENT = "solo-travel-planner/0.1"
```

- [ ] **Step 5: Add geocoding model**

Append to `apps/api/src/solo_api/models.py`:

```py
class CitySuggestion(BaseModel):
    id: str
    name: str
    country: str
    admin1: str | None = None
    latitude: float
    longitude: float
    timezone: str | None = None
```

- [ ] **Step 6: Implement Open-Meteo geocoding**

Create `apps/api/src/solo_api/geocoding.py`:

```py
import httpx

from solo_api.http import DEFAULT_TIMEOUT
from solo_api.models import CitySuggestion

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


def search_cities(query: str, count: int = 5) -> list[CitySuggestion]:
    normalized_query = query.strip()
    if len(normalized_query) < 2:
        return []

    response = httpx.get(
        GEOCODING_URL,
        params={
            "name": normalized_query,
            "count": count,
            "language": "en",
            "format": "json",
        },
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()

    suggestions: list[CitySuggestion] = []
    for item in payload.get("results", []):
        if not item.get("name") or not item.get("country"):
            continue
        suggestions.append(
            CitySuggestion(
                id=str(item["id"]),
                name=item["name"],
                country=item["country"],
                admin1=item.get("admin1"),
                latitude=item["latitude"],
                longitude=item["longitude"],
                timezone=item.get("timezone"),
            )
        )
```

- [ ] **Step 7: Expose geocoding endpoint**

In `apps/api/src/solo_api/main.py`, import:

```py
from solo_api.geocoding import search_cities
from solo_api.models import CitySuggestion
```

Add endpoint:

```py
@app.get("/geocode/cities")
def geocode_cities(query: str, count: int = 5) -> list[CitySuggestion]:
    return search_cities(query=query, count=count)
```

- [ ] **Step 8: Run API tests**

Run:

```powershell
cd apps/api; .venv\Scripts\python.exe -m pytest tests/test_geocoding.py -o cache_dir=C:\tmp\solo-pytest-cache
```

Expected: PASS.

- [ ] **Step 9: Commit**

```powershell
git add apps/api/pyproject.toml apps/api/src/solo_api/http.py apps/api/src/solo_api/geocoding.py apps/api/src/solo_api/models.py apps/api/src/solo_api/main.py apps/api/tests/test_geocoding.py
git commit -m "feat: add city geocoding endpoint"
```

---

### Task 5: Lock Home City Editing And Use Autocomplete Coordinates

**Files:**
- Modify: `apps/web/src/lib/types.ts`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/destination-map.tsx`
- Modify: `apps/web/src/app/page.test.tsx`

- [ ] **Step 1: Add failing page tests**

Add these tests to `apps/web/src/app/page.test.tsx`:

```tsx
it("keeps the saved home city immutable until the edit button is clicked", () => {
  render(<Page />);

  expect(screen.getByDisplayValue("London")).toBeDisabled();
  expect(screen.getByRole("button", { name: "Edit home city" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Edit home city" }));

  expect(screen.getByDisplayValue("London")).toBeEnabled();
});

it("autocompletes home city and stores selected coordinates", async () => {
  const fetchMock = vi.fn(async (url: string) => {
    if (url.includes("/geocode/cities")) {
      return {
        ok: true,
        json: async () => [
          {
            id: "2643743",
            name: "London",
            country: "United Kingdom",
            admin1: "England",
            latitude: 51.5085,
            longitude: -0.1257,
            timezone: "Europe/London",
          },
        ],
      };
    }

    return {
      ok: true,
      json: async () => [],
    };
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<Page />);

  fireEvent.click(screen.getByRole("button", { name: "Edit home city" }));
  fireEvent.change(screen.getByLabelText("Home city"), { target: { value: "Lon" } });

  await waitFor(() => {
    expect(screen.getByRole("button", { name: "London, England, United Kingdom" })).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole("button", { name: "London, England, United Kingdom" }));

  expect(screen.getByDisplayValue("London")).toBeDisabled();
  expect(screen.getByText("London home base")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
corepack pnpm --filter @solo/web test -- --run src/app/page.test.tsx
```

Expected: FAIL because home city is freely editable and autocomplete does not exist.

- [ ] **Step 3: Add frontend types**

Append to `apps/web/src/lib/types.ts`:

```ts
export type Coordinates = {
  latitude: number;
  longitude: number;
};

export type CitySuggestion = Coordinates & {
  id: string;
  name: string;
  country: string;
  admin1?: string | null;
  timezone?: string | null;
};

export type HomeLocation = Coordinates & {
  city: string;
  country: string;
  admin1?: string | null;
};
```

- [ ] **Step 4: Add API fetcher**

Modify `apps/web/src/lib/api.ts`:

```ts
import type {
  CitySuggestion,
  RecommendationGroup,
  RecommendationRequest,
} from "./types";

export async function fetchCitySuggestions(query: string): Promise<CitySuggestion[]> {
  const response = await fetch(
    `${apiBaseUrl}/geocode/cities?query=${encodeURIComponent(query)}&count=5`,
  );

  if (!response.ok) {
    throw new Error(`City suggestion request failed with ${response.status}`);
  }

  return response.json();
}
```

- [ ] **Step 5: Update map props for home coordinates and destination visibility**

In `apps/web/src/app/destination-map.tsx`, change props to:

```ts
type DestinationMapProps = {
  destinations: MapDestination[];
  homeCity: string;
  homeCoordinates: [number, number];
  showDestinationPins: boolean;
};
```

Change the function signature:

```ts
export function DestinationMap({
  destinations,
  homeCity,
  homeCoordinates,
  showDestinationPins,
}: DestinationMapProps) {
```

Change home marker color and coordinates:

```ts
const homeMarker = new maplibregl.Marker({ color: "#d33b2f" })
  .setLngLat(homeCoordinates)
  .setPopup(new maplibregl.Popup({ offset: 18 }).setText(`${homeCity} home base`))
  .addTo(map);
```

Wrap destination marker rendering:

```ts
if (showDestinationPins) {
  visibleDestinations.forEach((destination) => {
    const marker = new maplibregl.Marker({ color: "#24745a" })
      .setLngLat(destination.coordinates)
      .setPopup(
        new maplibregl.Popup({ offset: 18 }).setText(
          `${destination.city}, ${destination.country}: ${destination.score}. ${destination.summary}`,
        ),
      )
      .addTo(map);
    markerRefs.current.push(marker);
  });
}
```

Update the effect dependencies:

```ts
}, [homeCity, homeCoordinates, isMapReady, showDestinationPins, visibleDestinations]);
```

Hide chips:

```tsx
{showDestinationPins
  ? visibleDestinations.map((destination) => (
      <div className="map-chip" key={destination.city}>
        {destination.city} {destination.score}
        <span>{destination.summary}</span>
      </div>
    ))
  : null}
```

- [ ] **Step 6: Implement home city edit flow**

In `apps/web/src/app/page.tsx`, import:

```ts
import { Edit2 } from "lucide-react";
import { fetchCitySuggestions, fetchRecommendations } from "@/lib/api";
import type { CitySuggestion, HomeLocation, RecommendationGroup, TravelWindow } from "@/lib/types";
```

Replace home city state:

```ts
const [homeLocation, setHomeLocation] = useState<HomeLocation>({
  city: "London",
  country: "United Kingdom",
  admin1: "England",
  latitude: 51.5072,
  longitude: -0.1276,
});
const [homeCityDraft, setHomeCityDraft] = useState("London");
const [isEditingHomeCity, setIsEditingHomeCity] = useState(false);
const [citySuggestions, setCitySuggestions] = useState<CitySuggestion[]>([]);
```

Add a derived home city:

```ts
const homeCity = homeLocation.city;
```

Add handler:

```ts
async function handleHomeCityDraftChange(value: string) {
  setHomeCityDraft(value);
  if (value.trim().length < 2) {
    setCitySuggestions([]);
    return;
  }

  try {
    const suggestions = await fetchCitySuggestions(value);
    setCitySuggestions(suggestions);
  } catch {
    setCitySuggestions([]);
  }
}

function handleSelectHomeCity(suggestion: CitySuggestion) {
  setHomeLocation({
    city: suggestion.name,
    country: suggestion.country,
    admin1: suggestion.admin1,
    latitude: suggestion.latitude,
    longitude: suggestion.longitude,
  });
  setHomeCityDraft(suggestion.name);
  setCitySuggestions([]);
  setIsEditingHomeCity(false);
}
```

Replace the home city label block with:

```tsx
<div className="home-city-control">
  <label htmlFor="home-city-input">Home city</label>
  <div className="home-city-row">
    <input
      id="home-city-input"
      value={homeCityDraft}
      disabled={!isEditingHomeCity}
      onChange={(event) => handleHomeCityDraftChange(event.target.value)}
    />
    <button
      className="icon-button"
      type="button"
      aria-label="Edit home city"
      onClick={() => setIsEditingHomeCity(true)}
    >
      <Edit2 size={17} aria-hidden="true" />
    </button>
  </div>
  {isEditingHomeCity && citySuggestions.length > 0 ? (
    <ul className="autocomplete-list" aria-label="Home city suggestions">
      {citySuggestions.map((suggestion) => (
        <li key={suggestion.id}>
          <button
            className="autocomplete-option"
            type="button"
            onClick={() => handleSelectHomeCity(suggestion)}
          >
            {suggestion.name}
            {suggestion.admin1 ? `, ${suggestion.admin1}` : ""}, {suggestion.country}
          </button>
        </li>
      ))}
    </ul>
  ) : null}
</div>
```

- [ ] **Step 7: Pass map coordinates and date-range gate**

In `page.tsx`, change the map call:

```tsx
<DestinationMap
  destinations={mapDestinations}
  homeCity={homeCity}
  homeCoordinates={[homeLocation.longitude, homeLocation.latitude]}
  showDestinationPins={status === "ready"}
/>
```

- [ ] **Step 8: Run frontend tests**

Run:

```powershell
corepack pnpm --filter @solo/web test -- --run src/app/page.test.tsx
```

Expected: PASS.

- [ ] **Step 9: Commit**

```powershell
git add apps/web/src/lib/types.ts apps/web/src/lib/api.ts apps/web/src/app/page.tsx apps/web/src/app/destination-map.tsx apps/web/src/app/page.test.tsx
git commit -m "feat: add home city geocoding flow"
```

---

### Task 6: Add Destination Intelligence Backend Models And Cache

**Files:**
- Create: `apps/api/src/solo_api/cache.py`
- Modify: `apps/api/src/solo_api/models.py`
- Create: `apps/api/tests/test_destination_intelligence.py`

- [ ] **Step 1: Add failing model/cache tests**

Create `apps/api/tests/test_destination_intelligence.py` with initial tests:

```py
from datetime import date

from solo_api.cache import TtlCache
from solo_api.models import DestinationIntelligenceRequest


def test_ttl_cache_returns_value_before_expiry(monkeypatch):
    now = 1000.0
    monkeypatch.setattr("solo_api.cache.time.monotonic", lambda: now)
    cache = TtlCache(ttl_seconds=60)

    cache.set("lisbon", {"score": 1})

    assert cache.get("lisbon") == {"score": 1}


def test_ttl_cache_expires_value(monkeypatch):
    current = {"now": 1000.0}
    monkeypatch.setattr("solo_api.cache.time.monotonic", lambda: current["now"])
    cache = TtlCache(ttl_seconds=60)
    cache.set("lisbon", {"score": 1})

    current["now"] = 1061.0

    assert cache.get("lisbon") is None


def test_destination_intelligence_request_accepts_coordinates_and_dates():
    request = DestinationIntelligenceRequest(
        destination_city="Lisbon",
        country="Portugal",
        latitude=38.7223,
        longitude=-9.1393,
        start_date=date(2026, 5, 22),
        end_date=date(2026, 5, 25),
    )

    assert request.destination_city == "Lisbon"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
cd apps/api; .venv\Scripts\python.exe -m pytest tests/test_destination_intelligence.py -o cache_dir=C:\tmp\solo-pytest-cache
```

Expected: FAIL because cache and models do not exist.

- [ ] **Step 3: Implement TTL cache**

Create `apps/api/src/solo_api/cache.py`:

```py
import time
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    expires_at: float
    value: T


class TtlCache(Generic[T]):
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._values: dict[str, CacheEntry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._values.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._values.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._values[key] = CacheEntry(
            expires_at=time.monotonic() + self.ttl_seconds,
            value=value,
        )
```

- [ ] **Step 4: Add destination intelligence models**

Append to `apps/api/src/solo_api/models.py`:

```py
class DestinationIntelligenceRequest(BaseModel):
    destination_city: str
    country: str
    latitude: float
    longitude: float
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def ensure_valid_dates(self) -> "DestinationIntelligenceRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ClimateSummary(BaseModel):
    average_temperature_c: float | None
    precipitation_mm: float | None
    sunshine_hours: float | None
    summary: str
    source: str = "Open-Meteo"


class AttractionSummary(BaseModel):
    name: str
    category: str
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None
    source: str


class HotelPriceSummary(BaseModel):
    average_nightly_price: float | None
    median_nightly_price: float | None
    currency: str | None
    sample_size: int
    source: str = "Amadeus"
    status: Literal["available", "unavailable"] = "available"


class CostOfLivingSummary(BaseModel):
    currency: str
    meal_inexpensive: float | None = None
    coffee: float | None = None
    local_transport_ticket: float | None = None
    summary: str
    source: str


class DestinationIntelligence(BaseModel):
    destination_city: str
    country: str
    climate: ClimateSummary
    attractions: list[AttractionSummary]
    hotels: HotelPriceSummary
    cost_of_living: CostOfLivingSummary
```

- [ ] **Step 5: Run model/cache tests**

Run:

```powershell
cd apps/api; .venv\Scripts\python.exe -m pytest tests/test_destination_intelligence.py -o cache_dir=C:\tmp\solo-pytest-cache
```

Expected: PASS for the three initial tests.

- [ ] **Step 6: Commit**

```powershell
git add apps/api/src/solo_api/cache.py apps/api/src/solo_api/models.py apps/api/tests/test_destination_intelligence.py
git commit -m "feat: add destination intelligence models"
```

---

### Task 7: Add Climate, Attractions, Hotels, And Cost Providers

**Files:**
- Create: `apps/api/src/solo_api/weather.py`
- Create: `apps/api/src/solo_api/attractions.py`
- Create: `apps/api/src/solo_api/hotels.py`
- Create: `apps/api/src/solo_api/cost_of_living.py`
- Modify: `apps/api/tests/test_destination_intelligence.py`

- [ ] **Step 1: Add failing provider tests**

Append to `apps/api/tests/test_destination_intelligence.py`:

```py
from datetime import date

from solo_api.attractions import fetch_attractions
from solo_api.cost_of_living import StaticCostOfLivingProvider
from solo_api.hotels import summarize_hotel_prices
from solo_api.weather import fetch_climate_summary


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_fetch_climate_summary_uses_open_meteo(monkeypatch):
    calls = []

    def fake_get(url: str, params: dict, timeout):
        calls.append((url, params))
        return FakeResponse(
            {
                "daily": {
                    "temperature_2m_mean": [22.0, 24.0],
                    "precipitation_sum": [1.0, 3.0],
                    "sunshine_duration": [3600.0, 7200.0],
                }
            }
        )

    monkeypatch.setattr("solo_api.weather.httpx.get", fake_get)

    summary = fetch_climate_summary(
        latitude=38.7223,
        longitude=-9.1393,
        start_date=date(2026, 5, 22),
        end_date=date(2026, 5, 23),
    )

    assert summary.average_temperature_c == 23.0
    assert summary.precipitation_mm == 4.0
    assert summary.sunshine_hours == 3.0
    assert calls[0][0] == "https://archive-api.open-meteo.com/v1/archive"


def test_fetch_attractions_combines_overpass_and_wikimedia_results(monkeypatch):
    def fake_post(url: str, data: dict, headers: dict, timeout):
        return FakeResponse(
            {
                "elements": [
                    {
                        "id": 1,
                        "lat": 38.7139,
                        "lon": -9.1394,
                        "tags": {"name": "Castelo de Sao Jorge", "historic": "castle"},
                    },
                    {
                        "id": 2,
                        "lat": 38.6979,
                        "lon": -9.2067,
                        "tags": {"name": "Belem Tower", "tourism": "attraction"},
                    },
                ]
            }
        )

    def fake_get(url: str, timeout):
        assert url == "https://en.wikipedia.org/api/rest_v1/page/summary/Lisbon"
        return FakeResponse(
            {
                "extract": "Lisbon is Portugal's capital, known for hills, tiled streets, and maritime history."
            }
        )

    monkeypatch.setattr("solo_api.attractions.httpx.post", fake_post)
    monkeypatch.setattr("solo_api.attractions.httpx.get", fake_get)

    attractions = fetch_attractions(latitude=38.7223, longitude=-9.1393, city="Lisbon")

    assert [item.name for item in attractions] == ["Castelo de Sao Jorge", "Belem Tower"]
    assert attractions[0].category == "castle"
    assert attractions[0].description == "Lisbon is Portugal's capital, known for hills, tiled streets, and maritime history."


def test_hotel_summary_returns_unavailable_without_credentials(monkeypatch):
    monkeypatch.delenv("AMADEUS_CLIENT_ID", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_SECRET", raising=False)

    summary = summarize_hotel_prices(
        city_code="LIS",
        check_in_date=date(2026, 5, 22),
        check_out_date=date(2026, 5, 25),
    )

    assert summary.status == "unavailable"
    assert summary.sample_size == 0


def test_static_cost_of_living_provider_returns_city_summary():
    provider = StaticCostOfLivingProvider()

    summary = provider.summary_for(city="Lisbon", country="Portugal")

    assert summary.currency == "EUR"
    assert "Lisbon" in summary.summary
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
cd apps/api; .venv\Scripts\python.exe -m pytest tests/test_destination_intelligence.py -o cache_dir=C:\tmp\solo-pytest-cache
```

Expected: FAIL because provider modules do not exist.

- [ ] **Step 3: Implement Open-Meteo climate provider**

Create `apps/api/src/solo_api/weather.py`:

```py
from datetime import date

import httpx

from solo_api.http import DEFAULT_TIMEOUT
from solo_api.models import ClimateSummary

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def _average(values: list[float | None]) -> float | None:
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return None
    return round(sum(clean_values) / len(clean_values), 1)


def _sum(values: list[float | None], divisor: float = 1.0) -> float | None:
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return None
    return round(sum(clean_values) / divisor, 1)


def fetch_climate_summary(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> ClimateSummary:
    response = httpx.get(
        OPEN_METEO_ARCHIVE_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": "temperature_2m_mean,precipitation_sum,sunshine_duration",
            "timezone": "auto",
        },
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    daily = response.json().get("daily", {})

    average_temperature = _average(daily.get("temperature_2m_mean", []))
    precipitation = _sum(daily.get("precipitation_sum", []))
    sunshine_hours = _sum(daily.get("sunshine_duration", []), divisor=3600.0)
    summary = "Historical climate data is available for this travel window."
    if average_temperature is not None:
        summary = f"Average historical temperature is about {average_temperature}C for this window."

    return ClimateSummary(
        average_temperature_c=average_temperature,
        precipitation_mm=precipitation,
        sunshine_hours=sunshine_hours,
        summary=summary,
    )
```

- [ ] **Step 4: Implement Overpass attractions provider**

Create `apps/api/src/solo_api/attractions.py`:

```py
import httpx

from solo_api.http import DEFAULT_TIMEOUT, USER_AGENT
from solo_api.models import AttractionSummary

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
WIKIMEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"


def _category(tags: dict) -> str:
    for key in ("historic", "tourism", "amenity", "religion"):
        value = tags.get(key)
        if value:
            return str(value)
    return "point of interest"


def fetch_wikimedia_summary(city: str) -> str | None:
    response = httpx.get(
        WIKIMEDIA_SUMMARY_URL.format(title=city.replace(" ", "_")),
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    extract = response.json().get("extract")
    return extract if isinstance(extract, str) and extract else None


def fetch_attractions(
    latitude: float,
    longitude: float,
    city: str | None = None,
    radius_m: int = 6000,
) -> list[AttractionSummary]:
    query = f"""
    [out:json][timeout:20];
    (
      node(around:{radius_m},{latitude},{longitude})["tourism"~"museum|attraction|viewpoint|gallery"];
      node(around:{radius_m},{latitude},{longitude})["historic"];
      node(around:{radius_m},{latitude},{longitude})["amenity"="place_of_worship"];
      way(around:{radius_m},{latitude},{longitude})["tourism"~"museum|attraction|viewpoint|gallery"];
      way(around:{radius_m},{latitude},{longitude})["historic"];
    );
    out center tags 20;
    """
    response = httpx.post(
        OVERPASS_URL,
        data={"data": query},
        headers={"User-Agent": USER_AGENT},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()

    destination_summary = fetch_wikimedia_summary(city) if city else None
    attractions: list[AttractionSummary] = []
    seen_names: set[str] = set()
    for element in response.json().get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name")
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        center = element.get("center", {})
        attractions.append(
            AttractionSummary(
                name=name,
                category=_category(tags),
                latitude=element.get("lat", center.get("lat")),
                longitude=element.get("lon", center.get("lon")),
                description=destination_summary if not attractions else None,
                source="OpenStreetMap",
            )
        )
        if len(attractions) == 8:
            break

    return attractions
```

- [ ] **Step 5: Implement Amadeus hotel summary provider**

Create `apps/api/src/solo_api/hotels.py`:

```py
import os
from datetime import date
from statistics import median

import httpx

from solo_api.http import DEFAULT_TIMEOUT
from solo_api.models import HotelPriceSummary

AMADEUS_TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_HOTEL_OFFERS_URL = "https://test.api.amadeus.com/v3/shopping/hotel-offers"


def _credentials() -> tuple[str, str] | None:
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    return client_id, client_secret


def _access_token(client_id: str, client_secret: str) -> str:
    response = httpx.post(
        AMADEUS_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def summarize_hotel_prices(
    city_code: str,
    check_in_date: date,
    check_out_date: date,
) -> HotelPriceSummary:
    credentials = _credentials()
    if credentials is None:
        return HotelPriceSummary(
            average_nightly_price=None,
            median_nightly_price=None,
            currency=None,
            sample_size=0,
            status="unavailable",
        )

    token = _access_token(*credentials)
    response = httpx.get(
        AMADEUS_HOTEL_OFFERS_URL,
        params={
            "cityCode": city_code,
            "checkInDate": check_in_date.isoformat(),
            "checkOutDate": check_out_date.isoformat(),
            "adults": 1,
            "roomQuantity": 1,
            "bestRateOnly": "true",
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()

    prices: list[float] = []
    currency: str | None = None
    for item in response.json().get("data", []):
        for offer in item.get("offers", []):
            price = offer.get("price", {})
            total = price.get("total")
            if total is None:
                continue
            currency = currency or price.get("currency")
            prices.append(float(total))

    if not prices:
        return HotelPriceSummary(
            average_nightly_price=None,
            median_nightly_price=None,
            currency=currency,
            sample_size=0,
            status="unavailable",
        )

    nights = max(1, (check_out_date - check_in_date).days)
    nightly_prices = [price / nights for price in prices]
    return HotelPriceSummary(
        average_nightly_price=round(sum(nightly_prices) / len(nightly_prices), 2),
        median_nightly_price=round(median(nightly_prices), 2),
        currency=currency,
        sample_size=len(nightly_prices),
    )
```

- [ ] **Step 6: Implement static cost provider abstraction**

Create `apps/api/src/solo_api/cost_of_living.py`:

```py
from typing import Protocol

from solo_api.models import CostOfLivingSummary


class CostOfLivingProvider(Protocol):
    def summary_for(self, city: str, country: str) -> CostOfLivingSummary:
        ...


STATIC_COSTS: dict[tuple[str, str], CostOfLivingSummary] = {
    ("Lisbon", "Portugal"): CostOfLivingSummary(
        currency="EUR",
        meal_inexpensive=14.0,
        coffee=2.2,
        local_transport_ticket=2.0,
        summary="Lisbon is moderate for Western Europe, with food and transit usually friendly for solo weekends.",
        source="Static Numbeo-compatible seed",
    ),
    ("Seville", "Spain"): CostOfLivingSummary(
        currency="EUR",
        meal_inexpensive=13.0,
        coffee=1.8,
        local_transport_ticket=1.4,
        summary="Seville is relatively affordable, especially for casual meals, coffee, and local transit.",
        source="Static Numbeo-compatible seed",
    ),
    ("Porto", "Portugal"): CostOfLivingSummary(
        currency="EUR",
        meal_inexpensive=12.0,
        coffee=1.7,
        local_transport_ticket=1.8,
        summary="Porto keeps weekend costs manageable, with good value for meals and local movement.",
        source="Static Numbeo-compatible seed",
    ),
}


class StaticCostOfLivingProvider:
    def summary_for(self, city: str, country: str) -> CostOfLivingSummary:
        seeded = STATIC_COSTS.get((city, country))
        if seeded is not None:
            return seeded

        return CostOfLivingSummary(
            currency="EUR",
            summary=f"{city} has no static cost seed yet; show broad budget guidance until a live provider is configured.",
            source="Static Numbeo-compatible seed",
        )
```

- [ ] **Step 7: Run provider tests**

Run:

```powershell
cd apps/api; .venv\Scripts\python.exe -m pytest tests/test_destination_intelligence.py -o cache_dir=C:\tmp\solo-pytest-cache
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add apps/api/src/solo_api/weather.py apps/api/src/solo_api/attractions.py apps/api/src/solo_api/hotels.py apps/api/src/solo_api/cost_of_living.py apps/api/tests/test_destination_intelligence.py
git commit -m "feat: add destination data providers"
```

---

### Task 8: Orchestrate Destination Intelligence Endpoint

**Files:**
- Create: `apps/api/src/solo_api/destination_intelligence.py`
- Modify: `apps/api/src/solo_api/main.py`
- Modify: `apps/api/tests/test_destination_intelligence.py`

- [ ] **Step 1: Add failing endpoint aggregation tests**

Append to `apps/api/tests/test_destination_intelligence.py`:

```py
from fastapi.testclient import TestClient

from solo_api.main import app
from solo_api.models import AttractionSummary, ClimateSummary, HotelPriceSummary


def test_destination_intelligence_endpoint_aggregates_sources(monkeypatch):
    monkeypatch.setattr(
        "solo_api.destination_intelligence.fetch_climate_summary",
        lambda **kwargs: ClimateSummary(
            average_temperature_c=23.0,
            precipitation_mm=4.0,
            sunshine_hours=3.0,
            summary="Warm and bright.",
        ),
    )
    monkeypatch.setattr(
        "solo_api.destination_intelligence.fetch_attractions",
        lambda **kwargs: [
            AttractionSummary(name="Belem Tower", category="attraction", source="OpenStreetMap")
        ],
    )
    monkeypatch.setattr(
        "solo_api.destination_intelligence.summarize_hotel_prices",
        lambda **kwargs: HotelPriceSummary(
            average_nightly_price=121.5,
            median_nightly_price=118.0,
            currency="EUR",
            sample_size=12,
        ),
    )

    response = TestClient(app).post(
        "/destination-intelligence",
        json={
            "destination_city": "Lisbon",
            "country": "Portugal",
            "latitude": 38.7223,
            "longitude": -9.1393,
            "start_date": "2026-05-22",
            "end_date": "2026-05-25",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["destination_city"] == "Lisbon"
    assert payload["climate"]["average_temperature_c"] == 23.0
    assert payload["attractions"][0]["name"] == "Belem Tower"
    assert payload["hotels"]["median_nightly_price"] == 118.0
    assert payload["cost_of_living"]["currency"] == "EUR"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
cd apps/api; .venv\Scripts\python.exe -m pytest tests/test_destination_intelligence.py -o cache_dir=C:\tmp\solo-pytest-cache
```

Expected: FAIL because `/destination-intelligence` is not defined.

- [ ] **Step 3: Implement orchestrator**

Create `apps/api/src/solo_api/destination_intelligence.py`:

```py
import hashlib

from solo_api.attractions import fetch_attractions
from solo_api.cache import TtlCache
from solo_api.cost_of_living import StaticCostOfLivingProvider
from solo_api.hotels import summarize_hotel_prices
from solo_api.models import DestinationIntelligence, DestinationIntelligenceRequest
from solo_api.weather import fetch_climate_summary

INTELLIGENCE_CACHE: TtlCache[DestinationIntelligence] = TtlCache(ttl_seconds=60 * 60 * 6)

CITY_CODES = {
    ("Lisbon", "Portugal"): "LIS",
    ("Porto", "Portugal"): "OPO",
    ("Seville", "Spain"): "SVQ",
    ("Copenhagen", "Denmark"): "CPH",
}


def _cache_key(request: DestinationIntelligenceRequest) -> str:
    raw = "|".join(
        [
            request.destination_city,
            request.country,
            str(request.latitude),
            str(request.longitude),
            request.start_date.isoformat(),
            request.end_date.isoformat(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_destination_intelligence(
    request: DestinationIntelligenceRequest,
) -> DestinationIntelligence:
    key = _cache_key(request)
    cached = INTELLIGENCE_CACHE.get(key)
    if cached is not None:
        return cached

    city_code = CITY_CODES.get((request.destination_city, request.country), request.destination_city[:3].upper())
    intelligence = DestinationIntelligence(
        destination_city=request.destination_city,
        country=request.country,
        climate=fetch_climate_summary(
            latitude=request.latitude,
            longitude=request.longitude,
            start_date=request.start_date,
            end_date=request.end_date,
        ),
        attractions=fetch_attractions(
            latitude=request.latitude,
            longitude=request.longitude,
            city=request.destination_city,
        ),
        hotels=summarize_hotel_prices(
            city_code=city_code,
            check_in_date=request.start_date,
            check_out_date=request.end_date,
        ),
        cost_of_living=StaticCostOfLivingProvider().summary_for(
            city=request.destination_city,
            country=request.country,
        ),
    )
    INTELLIGENCE_CACHE.set(key, intelligence)
    return intelligence
```

- [ ] **Step 4: Expose endpoint**

In `apps/api/src/solo_api/main.py`, import:

```py
from solo_api.destination_intelligence import build_destination_intelligence
from solo_api.models import DestinationIntelligence, DestinationIntelligenceRequest
```

Add:

```py
@app.post("/destination-intelligence")
def destination_intelligence(
    request: DestinationIntelligenceRequest,
) -> DestinationIntelligence:
    return build_destination_intelligence(request)
```

- [ ] **Step 5: Run endpoint tests**

Run:

```powershell
cd apps/api; .venv\Scripts\python.exe -m pytest tests/test_destination_intelligence.py -o cache_dir=C:\tmp\solo-pytest-cache
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add apps/api/src/solo_api/destination_intelligence.py apps/api/src/solo_api/main.py apps/api/tests/test_destination_intelligence.py
git commit -m "feat: expose destination intelligence endpoint"
```

---

### Task 9: Render Destination Intelligence In The App

**Files:**
- Modify: `apps/web/src/lib/types.ts`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/page.test.tsx`

- [ ] **Step 1: Add failing frontend test**

Add this test to `apps/web/src/app/page.test.tsx`:

```tsx
it("loads destination intelligence for visible recommendations", async () => {
  const fetchMock = vi.fn(async (url: string) => {
    if (url.includes("/recommendations")) {
      return {
        ok: true,
        json: async () => [
          {
            travel_window: { id: "may", start_date: "2026-05-22", end_date: "2026-05-25" },
            recommendations: [
              {
                travel_window_id: "may",
                destination: {
                  id: "lisbon-pt",
                  city: "Lisbon",
                  country: "Portugal",
                  timezone: "Europe/Lisbon",
                  latitude: 38.7223,
                  longitude: -9.1393,
                  cost_level: 3,
                  short_stay_score: 5,
                  solo_friendliness: 5,
                  tags: [],
                  seasonal_strengths: {},
                  climate_notes: "",
                  caveats: [],
                },
                score: 91,
                reasons: ["Matches your preference for warmer destinations."],
                caveats: [],
              },
            ],
          },
        ],
      };
    }

    if (url.includes("/destination-intelligence")) {
      return {
        ok: true,
        json: async () => ({
          destination_city: "Lisbon",
          country: "Portugal",
          climate: {
            average_temperature_c: 23,
            precipitation_mm: 4,
            sunshine_hours: 9,
            summary: "Average historical temperature is about 23C for this window.",
            source: "Open-Meteo",
          },
          attractions: [{ name: "Belem Tower", category: "attraction", source: "OpenStreetMap" }],
          hotels: {
            average_nightly_price: 121,
            median_nightly_price: 118,
            currency: "EUR",
            sample_size: 12,
            source: "Amadeus",
            status: "available",
          },
          cost_of_living: {
            currency: "EUR",
            meal_inexpensive: 14,
            coffee: 2.2,
            local_transport_ticket: 2,
            summary: "Lisbon is moderate for Western Europe.",
            source: "Static Numbeo-compatible seed",
          },
        }),
      };
    }

    return { ok: true, json: async () => [] };
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<Page />);

  fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

  await waitFor(() => {
    expect(screen.getByText("23C average")).toBeInTheDocument();
  });
  expect(screen.getByText("Belem Tower")).toBeInTheDocument();
  expect(screen.getByText("EUR 118 median hotel")).toBeInTheDocument();
  expect(screen.getByText("Lisbon is moderate for Western Europe.")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
corepack pnpm --filter @solo/web test -- --run src/app/page.test.tsx
```

Expected: FAIL because destination intelligence fetch/rendering does not exist.

- [ ] **Step 3: Add frontend intelligence types**

Append to `apps/web/src/lib/types.ts`:

```ts
export type DestinationIntelligenceRequest = {
  destination_city: string;
  country: string;
  latitude: number;
  longitude: number;
  start_date: string;
  end_date: string;
};

export type DestinationIntelligence = {
  destination_city: string;
  country: string;
  climate: {
    average_temperature_c: number | null;
    precipitation_mm: number | null;
    sunshine_hours: number | null;
    summary: string;
    source: string;
  };
  attractions: Array<{
    name: string;
    category: string;
    latitude?: number | null;
    longitude?: number | null;
    description?: string | null;
    source: string;
  }>;
  hotels: {
    average_nightly_price: number | null;
    median_nightly_price: number | null;
    currency: string | null;
    sample_size: number;
    source: string;
    status: "available" | "unavailable";
  };
  cost_of_living: {
    currency: string;
    meal_inexpensive?: number | null;
    coffee?: number | null;
    local_transport_ticket?: number | null;
    summary: string;
    source: string;
  };
};
```

- [ ] **Step 4: Add API fetcher**

Modify imports in `apps/web/src/lib/api.ts`:

```ts
import type {
  CitySuggestion,
  DestinationIntelligence,
  DestinationIntelligenceRequest,
  RecommendationGroup,
  RecommendationRequest,
} from "./types";
```

Add:

```ts
export async function fetchDestinationIntelligence(
  request: DestinationIntelligenceRequest,
): Promise<DestinationIntelligence> {
  const response = await fetch(`${apiBaseUrl}/destination-intelligence`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Destination intelligence request failed with ${response.status}`);
  }

  return response.json();
}
```

- [ ] **Step 5: Fetch intelligence after recommendations**

In `apps/web/src/app/page.tsx`, import `fetchDestinationIntelligence` and type `DestinationIntelligence`.

Add state:

```ts
const [destinationIntelligence, setDestinationIntelligence] = useState<
  Record<string, DestinationIntelligence>
>({});
```

In `handleFindDestinations`, after `const results = await fetchRecommendations(...)`, add:

```ts
const activeWindow = results.find((group) => group.travel_window.id === selectedTravelWindowId)
  ?.travel_window;
const activeItems =
  results.find((group) => group.travel_window.id === selectedTravelWindowId)?.recommendations ??
  results[0]?.recommendations ??
  [];

const intelligenceEntries = await Promise.all(
  activeItems.slice(0, 3).map(async (item) => {
    const intelligence = await fetchDestinationIntelligence({
      destination_city: item.destination.city,
      country: item.destination.country,
      latitude: item.destination.latitude,
      longitude: item.destination.longitude,
      start_date: activeWindow?.start_date ?? selectedTravelWindow.start_date,
      end_date: activeWindow?.end_date ?? selectedTravelWindow.end_date,
    });
    return [item.destination.id, intelligence] as const;
  }),
);
setDestinationIntelligence(Object.fromEntries(intelligenceEntries));
```

- [ ] **Step 6: Render intelligence on recommendation cards**

Inside the recommendation card map, derive:

```ts
const id = "destination" in item ? item.destination.id : city;
const intelligence = destinationIntelligence[id];
```

Below the pills row, add:

```tsx
{intelligence ? (
  <div className="destination-intelligence">
    {intelligence.climate.average_temperature_c !== null ? (
      <span className="pill">{intelligence.climate.average_temperature_c}C average</span>
    ) : null}
    {intelligence.attractions[0] ? (
      <span className="pill">{intelligence.attractions[0].name}</span>
    ) : null}
    {intelligence.hotels.status === "available" &&
    intelligence.hotels.currency &&
    intelligence.hotels.median_nightly_price !== null ? (
      <span className="pill">
        {intelligence.hotels.currency} {Math.round(intelligence.hotels.median_nightly_price)} median hotel
      </span>
    ) : (
      <span className="pill">Hotel prices unavailable</span>
    )}
    <p className="muted">{intelligence.cost_of_living.summary}</p>
  </div>
) : null}
```

- [ ] **Step 7: Run frontend tests**

Run:

```powershell
corepack pnpm --filter @solo/web test -- --run src/app/page.test.tsx
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add apps/web/src/lib/types.ts apps/web/src/lib/api.ts apps/web/src/app/page.tsx apps/web/src/app/page.test.tsx
git commit -m "feat: show destination intelligence"
```

---

### Task 10: Final Verification And Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README env and API notes**

Add this section to `README.md`:

````md
## Destination data

Solo uses Open-Meteo geocoding and historical weather without API keys. Destination attractions come from OpenStreetMap Overpass queries. Hotel price summaries use Amadeus when these optional environment variables are present:

```powershell
$env:AMADEUS_CLIENT_ID="..."
$env:AMADEUS_CLIENT_SECRET="..."
```

When Amadeus credentials are absent, the API returns a hotel price summary with `status: "unavailable"` and the UI shows that prices are unavailable. Cost-of-living data currently uses a static Numbeo-compatible shape so a live provider can be added without changing the frontend contract.
````

- [ ] **Step 2: Run all tests**

Run:

```powershell
corepack pnpm test
```

Expected: PASS for web and API tests.

- [ ] **Step 3: Run frontend lint**

Run:

```powershell
corepack pnpm --filter @solo/web lint
```

Expected: PASS. If Next reports that no lint script is configured for the current Next version, record the exact output in the implementation handoff and rely on tests/build.

- [ ] **Step 4: Run production build**

Run:

```powershell
corepack pnpm --filter @solo/web build
```

Expected: PASS.

- [ ] **Step 5: Start local services for manual verification**

In terminal 1:

```powershell
corepack pnpm dev:web
```

In terminal 2:

```powershell
corepack pnpm dev:api
```

Expected:
- Web: `http://localhost:3000`
- API: `http://localhost:45655`

- [ ] **Step 6: Manual browser verification**

Open `http://localhost:3000` and verify:

- The calendar remains visible before and after saving a range.
- Saving a range clears the previous draft date highlight.
- Canceling an in-progress range draft clears the draft and returns to the `Add range` state.
- Adding more than six ranges shows `Previous ranges` and `Next ranges`.
- Home city input is disabled until the edit icon is clicked.
- Typing `Lon` shows London autocomplete; selecting it locks the input again.
- Home map marker is red.
- Destination pins appear only after clicking `Find destinations`.
- Recommendation cards show climate, attraction, hotel, and cost-of-living data.
- Text remains readable and does not overlap at desktop width and at mobile width around 390px.

- [ ] **Step 7: Commit documentation and any final fixes**

```powershell
git add README.md
git commit -m "docs: document destination data providers"
```

---

## Self-Review

**Spec coverage:**  
The plan covers date-range-driven pace in Task 2, range pagination, canceling range drafts, and clearing the saved draft range highlight in Task 3, responsive Tailwind/shadcn-style styling in Task 1, immutable editable home city with autocomplete/geolocation in Tasks 4 and 5, red home pin and destination pin gating in Task 5, Open-Meteo weather in Tasks 4 and 7, Overpass/Wikimedia-ready attractions through Task 7, Amadeus hotel prices in Task 7, cost-of-living abstraction in Task 7, and normalized aggregation in Tasks 6 through 9.

**Placeholder scan:**  
No task uses `TBD`, empty implementation notes, or unbounded "add tests" instructions. Each test, implementation, command, and expected result is spelled out.

**Type consistency:**  
Frontend types use `DestinationIntelligence`, `CitySuggestion`, and `HomeLocation`; backend types use matching Pydantic names. The new API functions and endpoint names match across frontend and backend.

---

Plan complete and saved to `docs/superpowers/plans/2026-05-16-next-step-goals.md`. Two execution options:

**1. Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
