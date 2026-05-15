# Shared Contracts

This package is intentionally small. The backend owns runtime validation through Pydantic models in `apps/api/src/solo_api/models.py`. The frontend mirrors the request and response shapes in `apps/web/src/lib/types.ts`.

When API schemas stabilize, generate OpenAPI-derived TypeScript types here instead of hand-maintaining duplicate types.
