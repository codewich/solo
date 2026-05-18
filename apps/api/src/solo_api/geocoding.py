from solo_api.models import CitySuggestion
from solo_api.storage import find_nearest_city, search_catalog_cities


def _suggestion_from_destination(destination) -> CitySuggestion:
    return CitySuggestion(
        id=destination.id,
        name=destination.city,
        country=destination.country,
        admin1=destination.region,
        latitude=destination.latitude,
        longitude=destination.longitude,
        timezone=destination.timezone,
    )


def search_cities(query: str, count: int = 5) -> list[CitySuggestion]:
    return [_suggestion_from_destination(city) for city in search_catalog_cities(query, count)]


def nearest_city(latitude: float, longitude: float) -> CitySuggestion | None:
    destination = find_nearest_city(latitude=latitude, longitude=longitude)
    return _suggestion_from_destination(destination) if destination else None
