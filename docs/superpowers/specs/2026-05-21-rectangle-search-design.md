# Rectangle Search Design

## Goal

Add an explicit rectangle search mode so users can choose destinations by drawing a bounded area on the map instead of searching by distance from the home city. The feature should make the active search mode obvious, keep radius search unchanged, and persist the chosen mode with saved travel-window recommendations.

## UX Design

The `Search area` panel gets a shadcn segmented control with two modes:

- `Radius`
- `Rectangle`

Only one mode is active at a time.

In `Radius` mode, the existing radius slider remains visible and the map renders the current search circle around the home city.

In `Rectangle` mode, the radius slider is hidden and replaced by rectangle controls:

- `Draw rectangle`
- `Redraw`
- `Clear`
- a compact selected-area summary using the rectangle bounds

The app preserves the previous radius value in state when switching away from radius mode, but it is not used while rectangle mode is active. The map renders only the rectangle overlay in rectangle mode.

`Find destinations` is disabled in rectangle mode until a rectangle exists. If the user switches back to radius mode, the saved radius value and radius circle return.

## Map Interaction

The first implementation uses a custom MapLibre rectangle interaction rather than adding a general drawing library.

When the user clicks `Draw rectangle`, the map enters drawing mode. Dragging on the map creates a rectangle from the drag start point to the current pointer position. On pointer release, the rectangle is normalized into:

- `west`
- `south`
- `east`
- `north`

The map disables panning while drawing and restores normal map interaction after the rectangle is completed or cancelled.

Antimeridian-crossing rectangles are out of scope for this version. The UI stores only normal `west < east` bounds.

## Frontend Data Flow

The page keeps explicit search state:

```ts
type SearchMode = "radius" | "rectangle"

type SearchBounds = {
  west: number
  south: number
  east: number
  north: number
}
```

`handleFindDestinations` sends:

- `search_mode`
- `search_bounds` when `search_mode === "rectangle"`
- existing radius fields when `search_mode === "radius"`
- existing population, excluded city, travel window, home city, and user fields

The recommendation loading flow remains the same after candidate cities are returned: render city cards, score cities in parallel, load intelligence, and update card order as scoring results arrive.

When a saved travel window is selected, the frontend restores the latest saved search metadata. If the saved search used rectangle mode, the UI switches to `Rectangle` and draws the saved rectangle overlay.

## Backend API

Add request models:

```py
SearchMode = Literal["radius", "rectangle"]

class SearchBounds(BaseModel):
    west: float
    south: float
    east: float
    north: float
```

Validation rules:

- `west` and `east` are within `[-180, 180]`
- `south` and `north` are within `[-90, 90]`
- `west < east`
- `south < north`
- rectangle mode requires `search_bounds`

Radius mode keeps the current behavior and ignores rectangle bounds.

## Storage

Persist search mode and bounds on `recommendation_searches`:

- `search_mode text not null default 'radius'`
- `search_bounds jsonb`

Because the remote database is managed in Supabase, the implementation includes a copy-runnable SQL file under `docs/` that adds these columns and any required constraints/indexes.

Saved recommendation results remain linked to the recommendation search. The existing replacement logic expands to include:

- `search_mode`
- normalized `search_bounds`
- radius
- minimum population
- candidate limit
- excluded city IDs
- home city

If any of these parameters change for the same travel window, old recommendation results are replaced by the new search results.

## Candidate Queries

Radius mode keeps the existing PostGIS `ST_DWithin` city query.

Rectangle mode adds a bounded city query:

```sql
longitude between :west and :east
and latitude between :south and :north
```

The query still applies:

- minimum population
- excluded city IDs
- home city exclusion
- limit
- ordering by population descending

PostGIS polygon containment is not required for the first version because the selected area is rectangular and the city table already stores latitude and longitude.

## Error Handling

If a rectangle search reaches the API without bounds, the API returns a validation error and the frontend shows the existing persistent sonner error.

If drawing is cancelled or cleared, rectangle mode remains active but `Find destinations` is disabled until a new rectangle is drawn.

If a saved search contains invalid or missing rectangle bounds, the frontend falls back to rectangle mode with no selected area and does not auto-search.

## Testing

API tests cover:

- rectangle request validation
- rectangle candidate query returns only cities inside bounds
- radius search remains unchanged
- recommendation search replacement when bounds change
- saved travel windows include latest `search_mode` and `search_bounds`

Frontend tests cover:

- switching between radius and rectangle modes
- hiding radius controls in rectangle mode
- disabling `Find destinations` until rectangle bounds exist
- sending rectangle payload with bounds
- restoring saved rectangle search metadata
- preserving existing radius payload behavior

## Acceptance Conditions

- Users can explicitly switch between radius and rectangle search.
- Radius search behavior is unchanged.
- Rectangle search cannot run until an area is drawn.
- Rectangle search returns only cities inside the selected bounds.
- The active search shape is clear on the map, with only one shape visible at a time.
- Saved travel windows restore their previous search mode and area.
- Changing rectangle bounds invalidates and replaces saved recommendations for that travel window.
- Existing recommendation skeleton, progress, scoring, and intelligence loading behavior still works.
- API tests, frontend tests, lint, and build pass.
