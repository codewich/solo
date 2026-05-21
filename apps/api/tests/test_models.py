from datetime import date

import pytest
from pydantic import ValidationError

from solo_api.models import RecommendationSearchCreateRequest, SearchBounds, TravelWindow


def test_travel_window_counts_inclusive_days():
    window = TravelWindow(id="may-bank", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25))

    assert window.duration_days == 3


def test_travel_window_keeps_minimal_planning_metadata():
    window = TravelWindow(
        id="warm-weekend",
        start_date=date(2026, 5, 22),
        end_date=date(2026, 5, 25),
        label="Warm long weekend",
        status="candidate",
    )

    assert window.label == "Warm long weekend"
    assert window.status == "candidate"


def test_travel_window_rejects_end_before_start():
    with pytest.raises(ValidationError):
        TravelWindow(id="bad", start_date=date(2026, 5, 25), end_date=date(2026, 5, 23))


def test_search_bounds_rejects_inverted_rectangle():
    with pytest.raises(ValidationError, match="west must be less than east"):
        SearchBounds(west=2, south=48, east=1, north=49)

    with pytest.raises(ValidationError, match="south must be less than north"):
        SearchBounds(west=1, south=49, east=2, north=48)


def test_rectangle_search_requires_bounds():
    with pytest.raises(ValidationError, match="search_bounds is required"):
        RecommendationSearchCreateRequest(
            travel_window=TravelWindow(
                id="may",
                start_date=date(2026, 5, 23),
                end_date=date(2026, 5, 25),
            ),
            home_city_id="2643743",
            search_mode="rectangle",
        )


def test_rectangle_search_accepts_bounds():
    request = RecommendationSearchCreateRequest(
        travel_window=TravelWindow(
            id="may",
            start_date=date(2026, 5, 23),
            end_date=date(2026, 5, 25),
        ),
        home_city_id="2643743",
        search_mode="rectangle",
        search_bounds=SearchBounds(west=-1, south=48, east=3, north=52),
    )

    assert request.search_mode == "rectangle"
    assert request.search_bounds is not None
    assert request.search_bounds.west == -1


def test_radius_search_ignores_bounds():
    request = RecommendationSearchCreateRequest(
        travel_window=TravelWindow(
            id="may",
            start_date=date(2026, 5, 23),
            end_date=date(2026, 5, 25),
        ),
        home_city_id="2643743",
        search_mode="radius",
        search_bounds=SearchBounds(west=-1, south=48, east=3, north=52),
    )

    assert request.search_mode == "radius"
    assert request.search_bounds is None

