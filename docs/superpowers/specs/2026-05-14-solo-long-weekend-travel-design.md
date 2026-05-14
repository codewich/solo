# Solo Long-Weekend Travel Planner Design

Date: 2026-05-14

## Summary

Solo is a planning-first web app for flexible solo travelers in Europe. It helps users choose where to travel for upcoming long weekends and other candidate date ranges. The first version focuses on home-city-based recommendations, highlighted bank holidays, multiple candidate travel windows, preference discovery, excluded destinations, destination shortlists, and AI-assisted itinerary generation sized to each selected date range.

Flight price monitoring is a future capability. The initial architecture keeps room for it through provider interfaces, saved trips, and planned monitor endpoints, but v1 does not depend on flight APIs.

## Product Goals

- Help a flexible traveler answer: "Where should I go for these upcoming dates?"
- Make bank holidays and long weekends visible in the date selection flow.
- Support multiple candidate travel windows so users can plan several trips across the year.
- Present travel windows and destinations together through an interactive calendar and map workspace.
- Recommend multiple destinations per travel window based on preferences, seasonality, destination fit, and exclusions.
- Generate useful, lightweight itineraries that match the selected travel window length and the user's preferred travel pace.
- Allow anonymous exploration, with optional Google SSO to save preferences, exclusions, travel windows, recommendations, itineraries, and trips.

## Non-Goals For V1

- Booking flights, hotels, restaurants, or attractions.
- Real-time flight price monitoring.
- Live event search, live weather forecasts, or live opening-hour validation.
- Password-based authentication.
- Group planning, voting, or shared trip collaboration.
- A full destination administration console.

## Target User

The first target user is a solo flexible traveler based in Europe. They have a home city, may have access to multiple airports, and want to use bank holidays or short date ranges to explore European cities. They may not know the destination upfront and want Solo to suggest cities or countries that fit their style, weather preferences, interests, and travel constraints.

## Product Flow

### First-Time Flow

1. The user enters their home city.
2. The user opens a calendar where relevant bank holidays are highlighted.
3. The user selects one or more candidate travel windows.
4. Solo asks preference questions covering pace, climate, food, history, museums, nightlife, nature, budget sensitivity, popularity preference, and comfort constraints.
5. The user excludes cities or countries they have already visited or do not want recommended.
6. Solo shows matching destinations on an interactive map and in a recommendation panel grouped by travel window.
7. The user opens a destination recommendation from the map or panel to see why it fits, seasonal notes, practical caveats, and an itinerary sized to the selected window.
8. The user can continue anonymously or sign in with Google to save their profile, exclusions, travel windows, recommendations, itineraries, and trips.

### Returning Flow

1. The user lands on a dashboard.
2. Their home city, preferences, exclusions, and saved travel windows are visible.
3. They add or adjust candidate date ranges.
4. Solo recommends destinations grouped by each travel window.
5. The user saves selected recommendations as planned trips.

### Future Flight-Monitoring Flow

1. The user saves a trip for a destination and travel window.
2. The user enables price monitoring for that trip.
3. A background worker checks flight providers or aggregators.
4. Solo notifies the user when route, price, or direct-flight conditions match their rules.

## Architecture

Solo will be a fullstack monorepo.

### `apps/web`

TypeScript web app using Next.js. Responsibilities:

- Guided first-time onboarding.
- Returning-user dashboard.
- Home city capture.
- Multi-range calendar selection with bank-holiday highlighting.
- Interactive map workspace showing destination fit for the selected travel window.
- Preference collection.
- Destination and country exclusions.
- Recommendation results grouped by travel window.
- Recommendation detail and itinerary views.
- Google SSO entry points.

### `apps/api`

Python API using FastAPI. Responsibilities:

- Session and authentication handling.
- User profile persistence.
- Travel window persistence.
- Destination data access.
- Recommendation orchestration.
- AI itinerary generation.
- Saved trip management.
- Future flight-monitor route and service boundaries.

### `packages/shared`

Shared contracts or generated types where useful. This package should stay small and practical. The main purpose is to keep frontend and backend request/response shapes aligned without creating a large cross-language abstraction.

## Core Services

### Recommendation Engine

The recommendation engine accepts:

- Home city.
- One or more travel windows.
- Preference profile.
- Excluded cities or countries.
- Destination candidates.
- Bank-holiday context.
- Seasonal destination metadata.

It returns ranked destinations per travel window, including scoring factors, explanation inputs, caveats, and itinerary-generation context.

### Destination Provider

The first provider uses curated seed data checked into the repository and loaded into Postgres. The provider interface must allow future providers to add or enrich candidates from live search, weather, events, flight signals, or external travel data without changing the recommendation API.

V1 destination data should include:

- City and country.
- Coordinates and timezone.
- Nearby airport metadata where available.
- Tags such as food, history, museums, nightlife, nature, architecture, beach, warm, winter, underrated, popular, and slow-wander.
- Cost level.
- Solo-travel friendliness notes.
- Seasonal strengths.
- Climate notes.
- Suitability for short stays.

### Holiday Provider

The holiday provider returns relevant bank holidays for the user's home country or region and year. The frontend uses this to highlight candidate long weekends in the calendar. The provider should be replaceable so v1 can start with a simple library or static source and later improve regional accuracy.

### AI Planner

The AI planner generates:

- Personalized destination explanations.
- Window-aware itineraries sized to the selected date range.
- Pacing aligned to the user's preference, such as rushed, balanced, or wandering.

The AI planner should receive structured recommendation context and destination facts. It should not be the only source of durable destination data.

### Auth

Authentication is optional in v1. Anonymous users can explore the product. Google SSO lets users save durable preferences, exclusions, travel windows, recommendations, itineraries, and trips. Password authentication is out of scope.

## Data Model

### `User`

Stores Google SSO identity, home city, locale or country, and timestamps.

### `PreferenceProfile`

Stores travel style answers, including pace, climate preference, interest weights, budget sensitivity, popularity preference, and comfort constraints.

### `ExcludedDestination`

Stores cities or countries the user has visited or does not want recommended.

### `TravelWindow`

Represents a selected date range with start date, end date, optional label, linked bank holiday if any, flexibility notes, and status such as `candidate`, `planned`, or `archived`.

### `Destination`

Stores curated destination records and structured metadata for recommendation.

### `RecommendationRun`

Stores the input snapshot and generated rankings for one or more travel windows.

### `Recommendation`

Links a travel window to a destination with score, ranking factors, explanation, caveats, and summary.

### `Itinerary`

Stores a light travel plan sized to the selected travel window.

### `Trip`

Represents a saved plan: travel window, destination, itinerary, and user notes.

### `FlightMonitor`

Future table for route candidates, threshold rules, provider status, notification settings, and monitor history.

## API Shape

### `/auth`

Google SSO callback and session handling. Anonymous session support should be available for first-time exploration.

### `/profile`

Home city, locale, preference profile, and excluded destinations.

### `/holidays`

Returns bank holidays for a country or region and year.

### `/travel-windows`

Creates, updates, deletes, and lists selected travel windows.

### `/recommendations`

Runs destination ranking for one or more travel windows. Results are grouped by travel window.

### `/itineraries`

Generates or retrieves a window-aware itinerary for a selected recommendation.

### `/trips`

Saves selected recommendations and itineraries as planned trips.

### `/flight-monitors`

Reserved for future price monitoring. The route shape can exist as a disabled or unimplemented boundary, but v1 should not expose a broken user-facing feature.

## Testing Strategy

Backend tests should cover:

- Recommendation filtering respects excluded destinations.
- Multiple travel windows receive separate rankings.
- Date ranges calculate duration correctly.
- Bank-holiday data returns predictable results.
- Itinerary generation receives structured inputs with the correct duration and pacing.

Frontend tests should cover:

- Onboarding collects home city, preferences, exclusions, and multiple travel windows.
- Calendar highlights bank holidays and supports multiple date ranges.
- Recommendation results are grouped by travel window.
- Signed-out users can explore.
- Signed-in users can save preferences, exclusions, travel windows, trips, and itineraries.

## First Milestone

The first milestone is a working local app where a user can:

1. Enter a home city.
2. Select multiple candidate travel windows from a bank-holiday-aware calendar.
3. Set travel preferences.
4. Exclude visited or unwanted destinations.
5. Get seeded destination recommendations grouped by travel window.
6. Open a recommendation and generate a window-aware itinerary.
7. Optionally sign in with Google to save their profile and plans.

## Deployment Direction

Use a simple managed deployment path:

- Frontend on Vercel.
- Python API on Render, Fly, or Railway.
- Managed Postgres.
- Background worker added later for flight monitoring.

This path keeps the first version deployable without requiring a full cloud-native infrastructure build upfront.
