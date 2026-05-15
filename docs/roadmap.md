# Solo Roadmap

Solo should grow from a local recommendation prototype into a planning workspace for flexible European trips. The roadmap favors a useful solo-traveler flow first, then durable accounts, AI planning, live data, and flight monitoring.

## Current MVP Baseline

Status: implemented in the `solo-mvp` worktree.

The first vertical slice is in place:

- Root monorepo tooling with `pnpm`, a Next.js web app, a FastAPI backend, shared contract notes, and curated seed data.
- FastAPI routes for `/health`, `/holidays`, `/recommendations`, and `/itineraries`.
- Pydantic domain models for travel windows, preferences, destinations, recommendations, and itinerary requests.
- Seeded European destinations with recommendation metadata, seasonal strengths, caveats, and simple scoring.
- Deterministic itinerary drafts that match the selected travel-window duration and pace.
- A first-screen web workspace with three coordinated areas: left travel-window/preferences panel, center CSS-positioned Europe map, and right recommendation panel.
- Frontend tests for the page workflow, API-backed recommendations, and date-window formatting.
- Backend tests for health, models, destination loading, holidays, recommendations, and itineraries.

The MVP is intentionally deterministic. Local browser state, static bank-holiday data, curated destination data, and the CSS map are product scaffolding for the next milestone, not the final architecture.

## Product Principles

- Help the user decide where to go before asking them to book anything.
- Treat dates as the center of the product: bank holidays, flexible ranges, and saved candidate trips should drive the experience.
- Recommend multiple destinations before narrowing to one best plan.
- Keep city-level choices first. Airports can enrich routing later, but users think in home cities and destinations.
- Let users exclude places they already visited or do not want to revisit.
- Make future live-data integrations replaceable behind provider interfaces.

## Phase 1: Planning Workspace Upgrade

Goal: upgrade the implemented MVP from a deterministic prototype into a real planning surface.

### MVP Surface Already Done

- A travel-window-aware recommendation flow exists.
- The web app shows home city, preference lens, candidate ranges, a mock map, and ranked recommendations in one workspace.
- The API can return grouped recommendations for multiple travel windows.
- The API can draft an itinerary whose day count matches the selected window.
- UK 2026 bank holidays are available through the backend and highlighted in the first calendar surface.

The remaining Phase 1 work should build on these pieces rather than recreate them.

### City Autocomplete

Integrate with a place or geocoding service so users can set their home city through autocomplete rather than typing free text.

Candidate services:

- Google Places API: strong city search and familiar UX, but requires API keys and billing setup.
- Mapbox Geocoding API: pairs naturally with a Mapbox map, good city search, also requires billing setup.
- GeoNames or OpenStreetMap Nominatim: lower-cost options, but need careful rate-limit and data-quality handling.

The selected home city should store a stable place identifier, display name, country, coordinates, and timezone when available. This lets Solo recommend from London as a city even when London has several airports.

### Real Map

Replace the CSS mock map with a real interactive map in the center of the workspace.

Expected behavior:

- Show the user's home city marker.
- Show ranked destination markers for the selected travel range.
- Use marker styling to communicate score, recommendation rank, and selected state.
- Clicking a destination marker selects the destination and opens matching reasons, caveats, and itinerary preview.
- The map should remain useful before search results by showing the home city and an empty destination state.

Map candidates:

- Mapbox GL JS: polished, strong geocoding pairing, paid usage model.
- MapLibre GL JS: open-source map rendering, flexible tile-provider choice.
- Leaflet: simpler and lighter, good for early city-marker use cases.

Recommended first implementation: MapLibre or Leaflet unless we choose Mapbox for autocomplete at the same time.

### Multi-Range Calendar

The MVP calendar shows one month and lets the user adjust the first candidate range. It should become a proper multi-range workflow.

Expected behavior:

- Calendar still focuses on one visible month at a time.
- The user selects a start and end date on the calendar.
- An **Add range** button adds the selected range to a separate range list.
- The range list shows every candidate trip range the user has added.
- Each range can be selected, renamed, edited, or removed.
- Selecting a range in the list updates the map recommendations and itinerary panel for that range.
- The selected range should visually connect the calendar, range list, map pins, recommendation panel, and itinerary preview.
- Bank holidays should stay highlighted in the calendar and should be attached to added ranges when relevant.

Initial range-list fields:

- Start date.
- End date.
- Display label.
- Linked bank holiday name when available.
- Status: candidate, planned, or archived.
- Notes for flexibility or intent, such as "warm long weekend" or "Christmas market".

## Phase 2: Personalization And Saved Trips

Goal: let Solo remember the traveler.

- Add Google SSO.
- Persist home city, preferences, excluded destinations, travel ranges, recommendation runs, itineraries, and saved trips.
- Add a returning-user dashboard.
- Let users mark destinations as visited or excluded from future suggestions.
- Add trip status transitions: candidate, shortlisted, planned, completed, archived.

## Phase 3: AI Planning

Goal: move from deterministic itinerary drafts to useful AI-assisted plans.

- Generate itinerary options for the selected range and destination.
- Use structured recommendation context instead of vague prompts.
- Include pacing controls: rushed, balanced, wandering.
- Include user interests and exclusions in the itinerary prompt.
- Support regeneration with constraints such as "less museums", "more food", or "slower mornings".
- Store generated plans so users can compare versions.

## Phase 4: Live Destination Intelligence

Goal: make recommendations timely without making the product brittle.

- Replace static bank-holiday data with a regional holiday provider.
- Add seasonal weather signals or live forecast summaries.
- Add special-event signals for festivals, public holidays, exhibitions, and seasonal markets.
- Add destination freshness metadata so Solo can explain whether a signal came from curated data or live search.
- Keep live providers optional. If a provider fails, Solo should still return curated recommendations with a clear caveat.

## Phase 5: Flight Signals And Monitoring

Goal: help users act when a trip becomes affordable or convenient.

- Add route-candidate discovery from the selected home city to destination city airports.
- Add flight price monitor rules for saved trips.
- Track direct-flight availability, duration, price threshold, and departure airport preferences.
- Add background worker checks.
- Notify users when a route matches their rule.
- Keep booking out of scope unless the product direction changes later.

## Technical Foundations

- Introduce durable persistence with Postgres before Google SSO ships.
- Keep provider interfaces for places, maps, holidays, weather, events, AI, and flights.
- Generate frontend types from the FastAPI OpenAPI schema once API contracts stabilize.
- Add feature flags for live providers so local development remains deterministic.
- Add observability before background monitoring becomes user-facing.

## Near-Term Implementation Order

1. Promote the MVP travel-window shape into a richer frontend/API range model with labels, linked holidays, status, notes, and stable selection state.
2. Build the range-list UI with add, edit, select, rename, archive, and remove behavior.
3. Wire selected range state through recommendations, map pins, and itinerary preview instead of always emphasizing the first recommendation group.
4. Replace the CSS map with Leaflet or MapLibre and render destination markers from API coordinates.
5. Add city autocomplete and persist the selected home city metadata locally.
6. Add local persistence for candidate ranges, preferences, exclusions, and shortlist state.
7. Add Postgres-backed persistence and Google SSO.
8. Add AI itinerary generation using the existing deterministic itinerary contract as the fallback shape.
9. Add live destination signals behind provider interfaces.
10. Add flight monitoring.

## Explicit Non-Goals For The Next Milestone

- Booking flights, hotels, restaurants, or attractions.
- Social trip planning or group voting.
- Password authentication.
- A full destination admin console.
- Fully live search for every recommendation signal.
