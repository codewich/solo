# Parallel Recommendation Search Design

## Goal

Build a recommendation flow that feels responsive when search radius or filters change, persists signed-in user travel windows and recommendations, and removes unavailable hotel/cost features from the product surface.

## Scope

This design covers the next implementation batch:

- DB-only candidate city search with no location/radius result cache.
- Parallel per-city scoring and intelligence requests.
- Real progress based on completed API work.
- Saved user travel windows and overwritten saved recommendations.
- Home city selection from the city catalog, current-location nearest-city lookup, and city exclusions.
- Recommendation card and search UI cleanup.
- Vercel CORS configuration.

It does not add flight alerts, hotel pricing, payments, or preference profiling.

## Decisions

- Use parallel endpoint fan-out rather than SSE.
- Automatically retry each scoring/intelligence request twice.
- If a city still fails, render that card with an error state and a card-local retry button.
- Overwrite saved recommendations for the same user and travel window when the user searches again.
- Use an internal UUID user id. Store Google identity in a separate auth-account table.
- Keep city candidate search uncached. Cache and persist city facts and computed/provider data instead.

## API Shape

### `POST /recommendation-searches`

Creates or updates a search session for the signed-in user and target travel window.

Input:

```json
{
  "travel_window_id": "uuid-or-client-id",
  "home_city_id": "2643743",
  "radius_km": 1800,
  "min_population": 250000,
  "candidate_limit": 10,
  "excluded_city_ids": ["2267057"]
}
```

Behavior:

- Resolve the signed-in user.
- Create the travel window if it is new.
- Transactionally overwrite the prior search state for `user_id + travel_window_id`.
- Save search parameters and excluded cities.

Output:

```json
{
  "id": "search-id",
  "travel_window_id": "travel-window-id",
  "status": "created"
}
```

### `GET /recommendation-searches/{search_id}/cities`

Returns candidate cities quickly from PostGIS.

Behavior:

- Query the `cities` table only.
- Use home city coordinates as center.
- Apply radius, population, limit, and exclusions.
- Exclude the home city.
- Order by population descending.

Output:

```json
[
  {
    "id": "2267057",
    "city": "Lisbon",
    "country": "PT",
    "latitude": 38.7223,
    "longitude": -9.1393,
    "population": 544851
  }
]
```

### `POST /recommendation-searches/{search_id}/cities/{city_id}/score`

Scores one city.

Behavior:

- Read stored monthly climate by dominant travel-window month.
- Fetch and store monthly climate if missing.
- Read stored attractions; fetch and store if missing.
- Read/provider-cache air quality and Wikimedia summary/image.
- Persist the recommendation result.
- Return one recommendation card payload.

The dominant month is the month with most covered days in the date range. Ties use the later calendar date, so `2026-12-31` to `2027-01-01` uses January.

### `POST /recommendation-searches/{search_id}/cities/{city_id}/intelligence`

Loads city intelligence independently.

Behavior:

- Read stored attractions and climate first.
- Fetch/store missing attractions and climate.
- Return details that may arrive before or after the scored card is rendered.

## Retry And Progress

The frontend owns request orchestration.

Flow:

1. Create search session.
2. Fetch cities.
3. Render one skeleton card per city.
4. Start scoring requests for all cities in parallel.
5. Start intelligence requests for all cities in parallel.
6. As scores return, replace each skeleton with a card.
7. Sort cards by score after each score result.
8. As intelligence returns, attach it to the city by `city_id`.

Progress labels are derived from real counts:

- The primary Find Destinations button text carries the active progress state:
  - `Finding cities`
  - `Scoring 4/10`
  - `Loading details 7/10`
  - `Complete`
- Secondary progress UI may mirror these counts, but the button itself must always show the current active step while work is running.

Each scoring/intelligence request retries automatically twice. After three failed attempts total, the corresponding card shows an error message and a card-local retry button.

## Data Model

### `users`

```sql
id uuid primary key default gen_random_uuid(),
email text unique,
name text,
image_url text,
created_at timestamptz not null default now(),
updated_at timestamptz not null default now()
```

### `user_auth_accounts`

```sql
id bigserial primary key,
user_id uuid not null references users(id) on delete cascade,
provider text not null,
provider_subject text not null,
created_at timestamptz not null default now(),
unique(provider, provider_subject)
```

### `travel_windows`

```sql
id uuid primary key default gen_random_uuid(),
user_id uuid not null references users(id) on delete cascade,
label text,
start_date date not null,
end_date date not null,
status text not null default 'candidate',
created_at timestamptz not null default now(),
updated_at timestamptz not null default now()
```

### `recommendation_searches`

```sql
id uuid primary key default gen_random_uuid(),
user_id uuid not null references users(id) on delete cascade,
travel_window_id uuid not null references travel_windows(id) on delete cascade,
home_city_id text not null references cities(id),
radius_km integer not null,
min_population integer not null,
candidate_limit integer not null,
created_at timestamptz not null default now(),
updated_at timestamptz not null default now(),
unique(user_id, travel_window_id)
```

### `recommendation_excluded_cities`

```sql
search_id uuid not null references recommendation_searches(id) on delete cascade,
city_id text not null references cities(id) on delete cascade,
primary key(search_id, city_id)
```

### `recommendation_results`

```sql
search_id uuid not null references recommendation_searches(id) on delete cascade,
city_id text not null references cities(id) on delete cascade,
score integer not null,
payload jsonb not null,
created_at timestamptz not null default now(),
updated_at timestamptz not null default now(),
primary key(search_id, city_id)
```

Overwrite semantics:

- New search for the same `user_id + travel_window_id` updates `recommendation_searches`.
- It deletes/replaces `recommendation_excluded_cities`.
- It deletes/replaces `recommendation_results`.
- The operation is transactional.

Existing tables still used:

- `cities`: candidate search, home-city search, nearest-city lookup.
- `climate_normals`: monthly city climate read/write.
- `attractions`: city attraction read/write.
- `recommendation_scores`: deterministic component scores, retained unless replaced by `recommendation_results` in a later cleanup.
- `api_cache`: short-lived provider/computed cache.

Inactive tables:

- `airports`, `flight_alerts`, `flight_price_snapshots`, `hotel_price_snapshots` remain unused until those features exist.

## Authentication Boundary

The API must resolve the current user before reading or writing saved data.

Recommended first implementation:

- The Next.js app remains responsible for Google sign-in.
- The frontend passes an authenticated user context to the API through a server-mediated API helper or a signed session header.
- The API maps Google `sub` to `user_auth_accounts.provider_subject`.
- If no linked user exists, the API creates `users` and `user_auth_accounts`.

The exact transport can be implemented in the API split task, but all persisted user data must use internal `users.id`, not Google `sub`.

## Frontend UI

### Search Layout

The mock route will present 2-3 options:

- Option A: compact operational dashboard with dense controls and stacked cards.
- Option B: split planner with controls on the left, map/results center, live progress rail.
- Option C: staged queue with candidate skeletons, scored cards, and detail hydration.

The production UI should be selected from these mocks before implementation.

### Search States

- Disable range selection while searching.
- Disable Find Destinations while a search is active.
- After candidate cities return, show every candidate city immediately.
- Each candidate card shows its city/country header immediately.
- While a city is scoring or loading details, keep the card body as skeleton content.
- Do not render card-local status text such as `scored`, `details loaded`, or `details pending`; the skeleton state is enough.
- Keep card heights equal.
- Render long descriptions with line clamp/ellipsis.
- Render failed city cards with error text and retry button.
- If city details fail but scoring succeeds, show `N/A` in detail fields instead of unavailable copy.
- Reorder cards as scores arrive.
- Keep intelligence data keyed by `city_id`; it can arrive before the scored card renders.

### Error Handling

- Remove inline error text below Find Destinations.
- Use persistent Sonner toast with a close button.
- Toasts should show API `detail.message` when available.

### Remove Unavailable UI

Remove:

- Cost-of-living card content.
- Hotel price card content.
- Backend unavailable hotel/cost response fields.
- Related tests and styles.

Keep:

- Climate tags.
- Attraction count and top attraction details.
- Air quality status.
- Wikimedia summary/image.

### Climate And Air Quality Display

- Remove historical climate sentence from recommendation cards.
- Keep temperature/rain/sun tags.
- Remove air quality paragraph.
- Add colored air quality badge:
  - good: low PM2.5 / available and clean
  - moderate: acceptable PM2.5
  - poor: high PM2.5
  - unavailable: neutral

## Home City And Exclusions

Home city:

- Add autocomplete backed by the `cities` table.
- Only committed autocomplete selections are valid.
- Store selected home city id, name, country, coordinates.
- Add “Use current location”.
- Browser geolocation sends coordinates to an API endpoint that returns nearest DB city.

Exclusions:

- Add a shadcn `Command` + `Popover` city picker.
- Persist exclusions per search.
- Excluded cities and home city are omitted from candidate results.

## CORS Deployment

API env vars:

```env
CORS_ALLOWED_ORIGINS=https://your-web-domain.vercel.app
CORS_ALLOWED_ORIGIN_REGEX=https://.*\.vercel\.app
NEXTAUTH_URL=https://your-web-domain.vercel.app
```

Web env vars:

```env
NEXT_PUBLIC_API_URL=https://your-api-domain.vercel.app
```

Verification:

- From deployed web origin, call deployed API `/health`.
- Confirm `access-control-allow-origin` matches the deployed web origin.
- Confirm `POST /recommendations` or the new search creation endpoint succeeds from the deployed UI.

## Acceptance Criteria

- Changing only search radius performs one fast PostGIS city query and then parallel city scoring.
- Candidate skeleton count equals returned city count.
- The Find Destinations button text reflects real completed work.
- Scoring progress reflects completed scoring calls.
- Details progress reflects completed intelligence calls.
- All candidate city headers render before scoring finishes.
- Card body content stays skeletonized while scoring/details are loading.
- Cards do not show `scored`, `details loaded`, or `details pending` text.
- Detail failures render `N/A` fields.
- Failed city calls retry twice automatically.
- Failed city cards show a retry button after retries are exhausted.
- Range selection is disabled during search.
- No inline search error appears under the button.
- Persistent Sonner toast displays search errors.
- Cost-of-living and hotel pricing are absent from API responses and UI.
- No unavailable cost/hotel logic remains in active code paths.
- Recommendation cards have equal height and ellipsized descriptions.
- Climate cards show tags only, not the historical sentence.
- Air quality is shown as a colored badge, not a paragraph.
- Home city is selected only from DB-backed autocomplete or current-location nearest city.
- Home city is excluded from search results.
- User-selected excluded cities are excluded from search results.
- Signed-in users can save date ranges.
- Searching a date range overwrites saved recommendations for that user/range.
- Returning users can click a saved date range and load persisted recommendations.
- Vercel web can call Vercel API without CORS failure.

## Self-Review

- No placeholders remain.
- The plan covers all 17 requested items plus CORS deployment verification.
- The largest uncertainty is the auth transport from NextAuth to the API; the implementation plan must choose one concrete transport before coding persistence.
