# Solo

Solo is a planning-first travel web app for flexible solo travelers in Europe. It helps users choose destinations for bank holidays and other date ranges, compare multiple candidate travel windows, exclude places they have already visited, and draft window-aware itineraries.

## Apps

- `apps/web`: Next.js TypeScript frontend.
- `apps/api`: FastAPI Python backend.
- `data/destinations`: curated seed destination data.
- `packages/shared`: shared contract notes and generated artifacts when useful.

## Local Commands

```bash
corepack pnpm install
python -m venv apps/api/.venv
apps/api/.venv/bin/python -m pip install -e "apps/api[dev]"
corepack pnpm dev:web
corepack pnpm dev:api
corepack pnpm test
```

The local API defaults to `http://localhost:45655`, which matches the web app fallback.

## Local Infrastructure

Copy `.env.example` to `.env` and fill provider credentials as needed.

```bash
corepack pnpm docker:up
```

Docker starts:

- Postgres 16 with PostGIS
- Redis 7
- FastAPI on `http://localhost:45655`
- Next.js on `http://localhost:3000`

The Postgres container applies SQL files from `apps/api/migrations` on first database creation. For an existing Docker volume, apply new migrations manually or recreate the local volume.

## Data Storage

Durable data belongs in Postgres:

- cities
- countries
- airports
- attractions
- climate normals
- recommendation scores
- user saved destinations
- alerts and price snapshots

Short-lived provider responses belong in Redis or `api_cache` with TTLs:

- current weather: 1 hour
- air quality: 3 hours
- climate: 30 days
- attractions: 30 days
- hotel pricing: 7 days

Recommendation scoring is deterministic and does not use user preference inputs. The score is:

```text
travelScore = climateScore + attractionScore + popularityScore + affordabilityScore
```

Air quality is retained as context but is not part of the primary travel score.
