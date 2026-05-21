from solo_api.models import Destination
from solo_api.storage import (
    find_city_candidates,
    find_city_candidates_in_bounds,
    has_imported_city_catalog,
)


class CityCatalogNotReadyError(RuntimeError):
    pass


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
    if not has_imported_city_catalog():
        raise CityCatalogNotReadyError(
            "City catalog is not ready. Import GeoNames cities15000 into the cities table, "
            "then rerun recommendations."
        )

    destinations = find_city_candidates(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        min_population=min_population,
        limit=limit,
        region=region,
        query=query,
    )
    if destinations:
        return destinations

    return []


def search_city_candidates_in_bounds(
    *,
    west: float,
    south: float,
    east: float,
    north: float,
    min_population: int,
    limit: int,
    region: str | None = None,
    query: str | None = None,
) -> list[Destination]:
    if not has_imported_city_catalog():
        raise CityCatalogNotReadyError(
            "City catalog is not ready. Import GeoNames cities15000 into the cities table, "
            "then rerun recommendations."
        )

    destinations = find_city_candidates_in_bounds(
        west=west,
        south=south,
        east=east,
        north=north,
        min_population=min_population,
        limit=limit,
        region=region,
        query=query,
    )
    if destinations:
        return destinations

    return []
