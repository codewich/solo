from solo_api.attractions import fetch_attractions
from solo_api.models import AttractionSummary
from solo_api.storage import (
    get_cached_attractions,
    get_stored_attractions,
    is_provider_cache_disabled,
    set_cached_attractions,
    store_attractions,
)


def resolve_city_attractions(
    *,
    city_id: str | None,
    city: str,
    country: str,
    latitude: float,
    longitude: float,
    radius_m: int = 6000,
    use_cache: bool = True,
) -> list[AttractionSummary]:
    use_cache = use_cache and not is_provider_cache_disabled()
    if use_cache and city_id:
        stored = get_stored_attractions(city_id)
        if stored:
            return stored

    if use_cache:
        cached = get_cached_attractions(city_id=city_id, city=city, country=country)
        if cached is not None:
            return cached

    attractions = fetch_attractions(
        latitude=latitude,
        longitude=longitude,
        city=city,
        radius_m=radius_m,
    )

    if city_id and attractions:
        store_attractions(city_id=city_id, attractions=attractions)
    set_cached_attractions(
        city_id=city_id,
        city=city,
        country=country,
        attractions=attractions,
    )
    return attractions
