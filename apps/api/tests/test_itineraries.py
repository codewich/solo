from datetime import date

from solo_api.itineraries import ItineraryRequest, build_itinerary
from solo_api.models import TravelWindow


def test_itinerary_matches_window_duration():
    window = TravelWindow(
        id="long-weekend", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25)
    )

    itinerary = build_itinerary(destination_city="Lisbon", window=window)

    assert len(itinerary["days"]) == 3
    assert "pace" not in itinerary


def test_itinerary_endpoint_returns_days():
    request = ItineraryRequest(
        destination_city="Porto",
        travel_window={
            "id": "porto-trip",
            "start_date": "2026-06-12",
            "end_date": "2026-06-15",
        },
    )

    itinerary = build_itinerary(
        destination_city=request.destination_city,
        window=request.travel_window,
    )

    assert len(itinerary["days"]) == 4
