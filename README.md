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
apps/api/.venv/Scripts/python.exe -m pip install -e "apps/api[dev]"
corepack pnpm dev:web
corepack pnpm dev:api
corepack pnpm test
```

The local API defaults to `http://localhost:45655`, which matches the web app fallback.

The first milestone uses local browser state and deterministic API responses. Google SSO, Postgres persistence, live data providers, and flight monitoring come after the first vertical slice.
