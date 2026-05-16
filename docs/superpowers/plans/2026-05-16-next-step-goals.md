# 2026-05-16 Next Step Goals

## Brainstorm Result

The recommendation system should be backend-owned, date-range-aware, and powered by free live data where it is reliable enough for a planning prototype. The frontend should keep its current flow: the user selects or drafts a date range, clicks `Find destinations`, and receives ranked destinations for that range. Third-party APIs must stay behind the FastAPI service.

## Recommended Approach

Use seeded European destinations as the candidate set, then enrich each candidate with cached live signals:

- Open-Meteo historical archive for climate suitability.
- OpenStreetMap Overpass for attraction density and top attractions.
- Wikimedia summary as a popularity/context signal when available.
- Static/local cost-of-living data for affordability until a durable cost provider is added.

This is better than fully live city discovery for the current app because it gives real scoring inputs without expanding the candidate search problem, slowing every request, or making the UI brittle when one provider is unavailable.

## Tasks

1. Locate and replace seed-only recommendation scoring in `apps/api/src/solo_api/recommendations.py`.
2. Add cached recommendation signal orchestration in `apps/api/src/solo_api/recommendation_signals.py`.
3. Extend recommendation models with score breakdown, top attractions, best months, estimated daily budget, summary, and warning fields while preserving the existing response shape.
4. Add GET `/api/destinations/recommended?month=&budget=&region=&q=` for direct recommended destination search.
5. Keep the existing frontend `/recommendations` workflow compatible.
6. Add tests for live score breakdowns, cache reuse, provider fallback warnings, and the new direct endpoint.
7. Verify API tests, web tests, web build, Python lint, and one live smoke test.

## Exit Conditions

- `/recommendations` no longer ranks only from hardcoded seed metadata.
- The recommendation score is the sum of `climateScore`, `attractionScore`, `popularityScore`, and `affordabilityScore`.
- Live provider calls are cached by destination and travel-window dates.
- If Open-Meteo, Overpass, or Wikimedia fails, recommendations still return with warning context.
- The new direct endpoint returns sorted results shaped as:

```json
{
  "id": "lisbon-pt",
  "name": "Lisbon",
  "country": "Portugal",
  "coordinates": { "lat": 38.7223, "lng": -9.1393 },
  "travelScore": 77,
  "scoreBreakdown": {
    "climateScore": 35,
    "attractionScore": 25,
    "popularityScore": 5,
    "affordabilityScore": 12
  },
  "bestMonthsToVisit": ["March", "April", "May"],
  "topAttractions": ["Miradouro de São Pedro de Alcântara"],
  "estimatedDailyBudget": 36.4,
  "summary": null,
  "warning": "Wikimedia unavailable; popularity score used seed tags only."
}
```

## Completion Evidence

- Backend recommendation tests cover score breakdowns, cache reuse, fallback warnings, and the new endpoint.
- API suite passes.
- Web suite passes.
- Web production build passes.
- Live smoke test for Lisbon returns Open-Meteo and OSM-backed scores, then returns instantly from cache on the second call.
