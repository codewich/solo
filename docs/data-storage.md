```text
Act as a senior backend architect and database engineer.

The app already exists. Do NOT rebuild the application. Do NOT redesign the UI. Your goal is to inspect the current codebase and optimize the data architecture and infrastructure.

Context:

This is a travel recommendation app using:

- Next.js
- TypeScript
- Vercel deployment
- PostgreSQL
- PostGIS
- Redis
- MapLibre frontend

Current issues:

- Recommendation search still contains hardcoded logic
- Some data sources are hardcoded, unavailable, fake, or no longer usable
- Too much data is fetched dynamically
- Data persistence strategy is weak
- Repeated API calls occur unnecessarily
- Infrastructure setup is incomplete
- No proper local Docker workflow

Your job is NOT to rebuild the app.

Your job is to audit the codebase and safely improve architecture.

==================================================
PHASE 1 — AUDIT FIRST
==================================================

Before modifying code:

Inspect the existing codebase and identify:

1. Current models
2. Existing APIs
3. Recommendation logic
4. Hardcoded values
5. Mock providers
6. Unused providers
7. External API usage
8. Repeated API requests
9. Database setup
10. Existing Docker setup if any

Then provide:

1. Problems found
2. Suggested improvements
3. Files you plan to modify
4. Step-by-step implementation plan

Do NOT begin implementation immediately.

Keep changes minimal and safe.

==================================================
PHASE 2 — REMOVE BAD DATA SOURCES
==================================================

Audit all external data providers.

Remove:

- unavailable APIs
- dead APIs
- hardcoded fake production providers
- providers that cannot realistically be used
- deprecated integrations
- unreachable integrations

Examples:

- old Amadeus self-service references
- unavailable flight APIs
- placeholder hardcoded recommendation providers
- inactive hotel providers

Do not keep unsupported providers in production code.

If something is useful later:

Move it into:

docs/future-improvements.md

Document:

# Future Integrations

Flight APIs:
- Duffel
- Omio
- Kiwi affiliate
- NDC aggregators

Hotel APIs:
- future providers

Cost of living:
- future integrations

Travel scoring:
- future AI enhancements

Include:

- why it was removed
- requirements
- limitations
- estimated implementation complexity

==================================================
PHASE 3 — OPTIMIZE DATA ARCHITECTURE
==================================================

Reduce repeated external calls.

Move useful long-term data into database persistence.

Store permanently:

- cities
- countries
- airports
- attractions
- climate averages
- recommendation scores
- user saved destinations
- alerts
- flight snapshots
- hotel snapshots

Store as cache:

- weather
- air quality
- API responses
- provider responses

Store as snapshots:

- flight prices
- hotel prices
- recommendation recalculations
- optional AQI history

Suggested tables:

cities
countries
airports
attractions
climate_normals
recommendation_scores
flight_alerts
flight_price_snapshots
hotel_price_snapshots
user_saved_destinations
api_cache

Add new tables only if justified.

==================================================
SCHEMA GUIDELINES
==================================================

Cities:

- id
- name
- countryCode
- latitude
- longitude
- population
- timezone

Attractions:

- cityId
- coordinates
- attractionType
- source
- metadata JSONB

Climate:

Store monthly averages:

month
avgTempMin
avgTempMax
rainfall
sunshineHours

Recommendation scores:

Store component scores:

climateScore
attractionScore
affordabilityScore
popularityScore
airQualityScore
finalScore

==================================================
SCORING RULES
==================================================

Do NOT use AI as primary scoring.

Scoring must remain deterministic:

travelScore =
climateScore +
attractionScore +
popularityScore +
affordabilityScore

AI may only generate summaries.

Example:

"Lisbon is recommended because of mild weather, strong attraction density, and moderate travel costs."

==================================================
CACHE STRATEGY
==================================================

Current weather:

TTL:
1 hour

Air quality:

TTL:
3 hours

Climate:

TTL:
30 days

Attractions:

TTL:
30 days

Hotel pricing:

TTL:
7 days

Flight pricing:

daily snapshots

If Redis is unavailable:

Create DB-backed cache:

api_cache:

key
data JSONB
expiresAt

==================================================
DATABASE OPTIMIZATION
==================================================

Use:

PostgreSQL + PostGIS

Requirements:

- geo queries
- indexes
- composite indexes
- migration files
- schema optimization
- avoid over-normalization
- JSONB only where flexibility is useful

If Prisma exists:

- update Prisma schema
- generate migrations

If Drizzle exists:

- follow project convention

==================================================
PHASE 4 — LOCAL INFRASTRUCTURE
==================================================

Set up local infrastructure.

Requirements:

Local PostgreSQL
Local Redis
Docker support

Create/update:

docker-compose.yml

Services:

app
postgres
redis

Database:

Use PostgreSQL + PostGIS if possible.

Redis:

Use Redis for:

- cache
- rate limiting
- temporary storage

Avoid:

- queues
- worker systems
- unnecessary complexity

==================================================
DOCKER REQUIREMENTS
==================================================

All services must run inside Docker.

Do not use localhost communication.

Use Docker service names.

Example:

postgres
redis

Add:

persistent Docker volumes

Example:

postgres_data

Ensure:

docker compose up --build

starts the entire application.

==================================================
ENVIRONMENT SETUP
==================================================

Create/update:

.env.example

Include:

DATABASE_URL=

REDIS_URL=

NEXT_PUBLIC_*

API_KEYS

etc

==================================================
README
==================================================

Update README:

Include:

Local development setup

Docker usage

Commands:

docker compose up --build

Migration steps

Environment setup

Database notes

Redis notes

==================================================
IMPLEMENTATION RULES
==================================================

Do NOT massively refactor working code.

Prefer:

small safe changes

Keep UI behavior unchanged.

Keep API responses compatible.

Reuse existing architecture.

Avoid introducing unnecessary abstraction.

Focus on:

- persistence
- caching
- recommendation performance
- infrastructure
- cleanup

Implementation order:

1. Audit
2. Problems found
3. File list
4. Plan
5. Small changes
6. Verify app still works
```
