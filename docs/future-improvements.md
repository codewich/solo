# Future Integrations

## Flight APIs

- Duffel
- Omio
- Kiwi affiliate
- NDC aggregators

Removed from current implementation because there is no active flight provider integration or persistence workflow yet.

Requirements:
- Provider contract and production credentials
- Snapshot persistence in `flight_price_snapshots`
- Alert matching and retry handling

Limitations:
- Provider coverage and affiliate/commercial terms vary by market.
- Price freshness requires scheduled collection.

Estimated complexity: high.

## Hotel APIs

Removed the Amadeus self-service test hotel provider from production code. It used the test API and could not support reliable production pricing.

Requirements:
- Production hotel provider credentials
- City/property mapping
- Snapshot persistence in `hotel_price_snapshots`
- Cache TTL of 7 days

Limitations:
- Hotel APIs often require commercial approval and rate limits.
- Availability and pricing are highly volatile.

Estimated complexity: medium-high.

## Cost Of Living

Removed static Numbeo-compatible seed data from production scoring. It looked realistic but was hardcoded.

Requirements:
- Licensed or maintainable cost data source
- City-level normalization
- Freshness and source attribution

Limitations:
- Reliable cost-of-living data is often licensed.
- Sparse coverage can bias recommendation scores.

Estimated complexity: medium.

## Holiday Calendars

Removed the static GB 2026 holiday provider from the backend. The frontend still owns its current calendar highlights, but the API no longer presents a hardcoded holiday dataset as a production provider.

Requirements:
- Government or maintained calendar feed
- Country/year freshness checks
- Persistence or cache invalidation by country and year

Limitations:
- Substitute holidays and regional holidays vary by jurisdiction.

Estimated complexity: low-medium.

## Travel Scoring

Scoring remains deterministic. AI should only generate summaries after the deterministic component scores are available.

Future enhancements:
- Persist monthly climate normals
- Persist attraction density by city
- Add explainable score weighting experiments
- Generate human-readable summaries from stored score components

Estimated complexity: medium.
