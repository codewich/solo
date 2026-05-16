# Overpass OpenAQ Card Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Use live attraction counts, Wikimedia city imagery, and OpenAQ air quality in recommendation scoring and card presentation.

**Architecture:** Recommendation enrichment remains in `recommendation_signals.py`, with provider-specific modules hiding external API details. Scoring consumes compact signals: attraction count, city summary/image, cost, climate, and air quality. The frontend treats recommendation cards as the first-class destination surface and uses image URLs as progressive decoration.

**Tech Stack:** FastAPI, Pydantic, httpx, `overpass` Python wrapper, OpenAQ v3 HTTP API, Wikimedia REST summary API, Next.js/React, Vitest, pytest.

---

## Acceptance Conditions

- [x] Backend uses the `overpass` Python wrapper for Overpass requests.
- [x] Scoring uses an attraction count instead of a list of attraction objects.
- [x] Recommendation payloads include `attractionCount`, `airQuality`, and `imageUrl` when available.
- [x] Score breakdown includes `airQualityScore`.
- [x] OpenAQ failures are warnings and use a neutral score.
- [x] Wikimedia image failures are warnings or null image URLs, not request failures.
- [x] Recommendation cards use Wikimedia images as readable background imagery when available.
- [x] Tests cover provider parsing/fallbacks, scoring changes, API shape, and frontend card rendering.
- [x] Focused tests, full web tests, API tests, lint, and a browser health check pass.

## Task List

- [x] Add backend tests for attraction count, Wikimedia image URL, OpenAQ summary, scoring, and response aliases.
- [x] Install and wire the `overpass` dependency.
- [x] Refactor `attractions.py` to expose `count_attractions(...)`.
- [x] Add `air_quality.py` for OpenAQ nearest-location/latest measurements and scoring-friendly summary.
- [x] Extend Pydantic models and recommendation scoring.
- [x] Update frontend types, score tooltip, and recommendation card background UI.
- [x] Run verification and restart/check local services.
