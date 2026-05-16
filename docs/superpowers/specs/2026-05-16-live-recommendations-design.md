# Live Recommendations Design

## Goal

Replace seed-only recommendation scoring with a backend-owned live data pipeline that uses free data sources with cache-backed fallbacks. The existing web flow should keep calling the recommendation API and should not call third-party services directly.

## Approach

The seed destination list remains the candidate set for this slice. Each candidate is enriched per travel window with cached live signals:

- Open-Meteo historical archive climate for the selected date window.
- OpenStreetMap Overpass attraction density and top attraction names.
- Wikimedia page summary as a popularity and context proxy.
- Static/local cost-of-living data for affordability until a durable cost provider exists.

The scorer combines four normalized parts: `climateScore`, `attractionScore`, `popularityScore`, and `affordabilityScore`. Scores are sorted descending and returned through the existing `RecommendationGroup` shape, extended with optional score breakdown and live-data context. A new GET endpoint, `/api/destinations/recommended`, exposes the direct search shape requested in the next-step goal while reusing the same scorer.

## Error Handling And Cache

Live signals are stored in a TTL cache keyed by destination and travel-window dates. Provider failures do not fail the recommendation request. Failed signals produce a warning, fall back to seed/static values where possible, and allow the remaining signals to contribute to the score.

## Exit Conditions

- The hardcoded recommendation score path is replaced by live-signal scoring.
- Open-Meteo, Overpass, Wikimedia, and static cost are used server-side only.
- Cached recommendation signals prevent repeated live provider calls for the same destination/date key.
- Provider failures return recommendations with warning context instead of raising.
- Existing frontend behavior remains compatible with `/recommendations`.
- A GET `/api/destinations/recommended?month=&budget=&region=&q=` endpoint returns sorted recommended destinations with score breakdowns.
