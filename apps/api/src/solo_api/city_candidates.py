import os
from math import asin, cos, radians, sin, sqrt

import httpx

from solo_api.cache import CITY_CANDIDATE_TTL_SECONDS, TtlCache
from solo_api.http import DEFAULT_TIMEOUT
from solo_api.models import Destination
from solo_api.storage import find_city_candidates, get_cached_cities, set_cached_cities, upsert_cities

GEODB_CITIES_URL = "https://wft-geo-db.p.rapidapi.com/v1/geo/cities"
GEODB_HOST = "wft-geo-db.p.rapidapi.com"
GEODB_NATIVE_RADIUS_LIMIT_KM = 100
EUROPE_COUNTRY_IDS = ",".join(
    [
        "AT",
        "BE",
        "CH",
        "CZ",
        "DE",
        "DK",
        "ES",
        "FI",
        "FR",
        "GB",
        "GR",
        "HR",
        "HU",
        "IE",
        "IT",
        "NL",
        "NO",
        "PL",
        "PT",
        "SE",
    ]
)

CITY_CANDIDATE_CACHE: TtlCache[list[Destination]] = TtlCache(
    ttl_seconds=CITY_CANDIDATE_TTL_SECONDS
)


def _geodb_api_key() -> str:
    api_key = os.getenv("GEODB_RAPIDAPI_KEY")
    if not api_key:
        raise RuntimeError("GEODB_RAPIDAPI_KEY is required when city candidates are not in storage.")
    return api_key


def _location(latitude: float, longitude: float) -> str:
    lat_prefix = "+" if latitude >= 0 else ""
    lng_prefix = "+" if longitude >= 0 else ""
    return f"{lat_prefix}{latitude:.4f}{lng_prefix}{longitude:.4f}"


def _cache_key(
    *,
    latitude: float,
    longitude: float,
    radius_km: int,
    min_population: int,
    limit: int,
    region: str | None,
    query: str | None,
) -> str:
    return "|".join(
        [
            f"{latitude:.4f}",
            f"{longitude:.4f}",
            str(radius_km),
            str(min_population),
            str(limit),
            (region or "").strip().lower(),
            (query or "").strip().lower(),
        ]
    )


def _destination_from_geodb(item: dict) -> Destination | None:
    if not item.get("name") or not item.get("country"):
        return None
    latitude = item.get("latitude")
    longitude = item.get("longitude")
    if latitude is None or longitude is None:
        return None

    raw_id = item.get("wikiDataId") or item.get("id") or f"{item['name']}-{item['countryCode']}"
    return Destination(
        id=str(raw_id),
        city=item["name"],
        country=item["country"],
        country_code=item.get("countryCode"),
        region=item.get("region"),
        timezone=item.get("timezone"),
        latitude=latitude,
        longitude=longitude,
        population=item.get("population"),
    )


def _distance_km(
    first_latitude: float,
    first_longitude: float,
    second_latitude: float,
    second_longitude: float,
) -> float:
    earth_radius_km = 6371.0
    lat1 = radians(first_latitude)
    lat2 = radians(second_latitude)
    delta_lat = radians(second_latitude - first_latitude)
    delta_lng = radians(second_longitude - first_longitude)
    haversine = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lng / 2) ** 2
    return 2 * earth_radius_km * asin(sqrt(haversine))


def _is_country_filter(value: str | None) -> bool:
    return bool(value and len(value.strip()) <= 3)


def search_city_candidates(
    *,
    latitude: float,
    longitude: float,
    radius_km: int,
    min_population: int,
    limit: int,
    region: str | None = None,
    query: str | None = None,
) -> list[Destination]:
    key = _cache_key(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        min_population=min_population,
        limit=limit,
        region=region,
        query=query,
    )
    cached = CITY_CANDIDATE_CACHE.get(key)
    if cached is not None:
        return cached

    persisted = find_city_candidates(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        min_population=min_population,
        limit=limit,
        region=region,
        query=query,
    )
    if persisted:
        CITY_CANDIDATE_CACHE.set(key, persisted)
        return persisted

    cached_payload = get_cached_cities(key)
    if cached_payload is not None:
        CITY_CANDIDATE_CACHE.set(key, cached_payload)
        return cached_payload

    uses_native_radius = radius_km <= GEODB_NATIVE_RADIUS_LIMIT_KM
    params = {
        "minPopulation": min_population,
        "limit": min(10, limit),
        "sort": "-population",
        "types": "CITY",
        "languageCode": "en",
    }
    if uses_native_radius:
        params["location"] = _location(latitude, longitude)
        params["radius"] = radius_km
        params["distanceUnit"] = "KM"
    else:
        params["countryIds"] = region if _is_country_filter(region) else EUROPE_COUNTRY_IDS

    if query:
        params["namePrefix"] = query
    if region and uses_native_radius:
        params["countryIds"] = region

    response = httpx.get(
        GEODB_CITIES_URL,
        params=params,
        headers={
            "X-RapidAPI-Key": _geodb_api_key(),
            "X-RapidAPI-Host": GEODB_HOST,
        },
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()

    destinations = [
        destination
        for destination in (_destination_from_geodb(item) for item in response.json().get("data", []))
        if destination is not None
    ]
    if not uses_native_radius:
        destinations = [
            destination
            for destination in destinations
            if _distance_km(latitude, longitude, destination.latitude, destination.longitude) <= radius_km
        ][:limit]
    upsert_cities(destinations)
    set_cached_cities(
        key=key,
        destinations=destinations,
        ttl_seconds=CITY_CANDIDATE_TTL_SECONDS,
        provider="GeoDB Cities",
    )
    CITY_CANDIDATE_CACHE.set(key, destinations)
    return destinations
