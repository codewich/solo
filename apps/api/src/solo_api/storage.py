from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from solo_api import database
from solo_api.cache import RedisJsonCache
from solo_api.config import get_env
from solo_api.models import AttractionSummary, ClimateSummary, Destination, RecommendationScoreBreakdown

REDIS_CACHE = RedisJsonCache(get_env("REDIS_URL") or get_env("REDIS_KV_URL"))


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def stable_cache_key(namespace: str, payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, default=_json_default)
    return f"{namespace}:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"


def get_api_cache(key: str) -> Any | None:
    raw_payload = REDIS_CACHE.get(key)
    if raw_payload is not None:
        return json.loads(raw_payload)
    if not database.is_database_configured():
        return None
    row = database.fetch_one(
        """
        select payload
        from api_cache
        where cache_key = %s
          and expires_at > now()
        """,
        [key],
    )
    return row["payload"] if row else None


def set_api_cache(key: str, payload: Any, ttl_seconds: int, provider: str) -> None:
    serialized_payload = json.dumps(payload, default=_json_default)
    REDIS_CACHE.set(key, serialized_payload, ttl_seconds)
    if not database.is_database_configured():
        return
    database.execute(
        """
        insert into api_cache (cache_key, provider, payload, expires_at)
        values (%s, %s, %s::jsonb, %s)
        on conflict (cache_key) do update set
          provider = excluded.provider,
          payload = excluded.payload,
          expires_at = excluded.expires_at,
          updated_at = now()
        """,
        [
            key,
            provider,
            serialized_payload,
            datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        ],
    )


def has_imported_city_catalog() -> bool:
    if not database.is_database_configured():
        return False

    row = database.fetch_one(
        """
        select 1
        from cities
        limit 1
        """
    )
    return row is not None


def find_city_candidates(
    *,
    latitude: float,
    longitude: float,
    radius_km: int,
    min_population: int,
    limit: int,
    region: str | None,
    query: str | None,
) -> list[Destination]:
    if not database.is_database_configured():
        return []

    rows = database.fetch_all(
        """
        select
          id,
          name as city,
          country_name as country,
          timezone,
          latitude,
          longitude,
          population,
          region,
          country_code
        from cities
        where population >= %s
          and (%s::text is null or country_code = upper(%s::text) or region ilike %s::text)
          and (%s::text is null or name ilike %s::text)
          and ST_DWithin(
            geography(ST_MakePoint(longitude, latitude)),
            geography(ST_MakePoint(%s, %s)),
            %s
          )
        order by population desc nulls last
        limit %s
        """,
        [
            min_population,
            region,
            region,
            f"%{region}%" if region else None,
            query,
            f"{query}%" if query else None,
            longitude,
            latitude,
            radius_km * 1000,
            limit,
        ],
    )
    return [Destination.model_validate(row) for row in rows]


def upsert_cities(destinations: list[Destination]) -> None:
    if not database.is_database_configured() or not destinations:
        return
    with database.connect() as connection:
        with connection.cursor() as cursor:
            for destination in destinations:
                cursor.execute(
                    """
                    insert into cities (
                      id, name, country_name, country_code, region, timezone,
                      latitude, longitude, population
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do update set
                      name = excluded.name,
                      country_name = excluded.country_name,
                      country_code = excluded.country_code,
                      region = excluded.region,
                      timezone = excluded.timezone,
                      latitude = excluded.latitude,
                      longitude = excluded.longitude,
                      population = excluded.population,
                      updated_at = now()
                    """,
                    [
                        destination.id,
                        destination.city,
                        destination.country,
                        destination.country_code,
                        destination.region,
                        destination.timezone,
                        destination.latitude,
                        destination.longitude,
                        destination.population,
                    ],
                )
        connection.commit()


def get_climate_normal(*, city_id: str, month: int, source: str = "Open-Meteo") -> ClimateSummary | None:
    if not database.is_database_configured():
        return None

    row = database.fetch_one(
        """
        select avg_temp_min, avg_temp_max, rainfall, sunshine_hours, source
        from climate_normals
        where city_id = %s
          and month = %s
          and source = %s
        """,
        [city_id, month, source],
    )
    if row is None:
        return None

    avg_temp_min = row["avg_temp_min"]
    avg_temp_max = row["avg_temp_max"]
    average_temperature = None
    if avg_temp_min is not None and avg_temp_max is not None:
        average_temperature = round((avg_temp_min + avg_temp_max) / 2, 1)

    summary = "Historical climate data is available for this month."
    if average_temperature is not None:
        summary = f"Average historical temperature is about {average_temperature}C for this month."

    return ClimateSummary(
        average_temperature_c=average_temperature,
        average_temperature_min_c=avg_temp_min,
        average_temperature_max_c=avg_temp_max,
        precipitation_mm=row["rainfall"],
        sunshine_hours=row["sunshine_hours"],
        summary=summary,
        source=row["source"],
    )


def store_climate_normal(
    *,
    city_id: str,
    month: int,
    climate: ClimateSummary,
    source: str,
) -> None:
    if not database.is_database_configured():
        return
    if (
        climate.average_temperature_c is None
        and climate.average_temperature_min_c is None
        and climate.average_temperature_max_c is None
        and climate.precipitation_mm is None
        and climate.sunshine_hours is None
    ):
        return

    avg_temp_min = (
        climate.average_temperature_min_c
        if climate.average_temperature_min_c is not None
        else climate.average_temperature_c
    )
    avg_temp_max = (
        climate.average_temperature_max_c
        if climate.average_temperature_max_c is not None
        else climate.average_temperature_c
    )
    database.execute(
        """
        insert into climate_normals (
          city_id, month, avg_temp_min, avg_temp_max, rainfall, sunshine_hours, source
        )
        values (%s, %s, %s, %s, %s, %s, %s)
        on conflict (city_id, month, source) do update set
          avg_temp_min = excluded.avg_temp_min,
          avg_temp_max = excluded.avg_temp_max,
          rainfall = excluded.rainfall,
          sunshine_hours = excluded.sunshine_hours,
          updated_at = now()
        """,
        [
            city_id,
            month,
            avg_temp_min,
            avg_temp_max,
            climate.precipitation_mm,
            climate.sunshine_hours,
            source,
        ],
    )


def get_stored_attractions(city_id: str) -> list[AttractionSummary]:
    if not database.is_database_configured():
        return []

    rows = database.fetch_all(
        """
        select name, attraction_type as category, latitude, longitude, source, metadata
        from attractions
        where city_id = %s
        order by id
        limit 12
        """,
        [city_id],
    )
    return [
        AttractionSummary(
            name=row["name"],
            category=row["category"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            description=(row.get("metadata") or {}).get("description"),
            source=row["source"],
        )
        for row in rows
    ]


def store_attractions(*, city_id: str, attractions: list[AttractionSummary]) -> None:
    if not database.is_database_configured() or not attractions:
        return

    with database.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from attractions where city_id = %s", [city_id])
            for attraction in attractions:
                cursor.execute(
                    """
                    insert into attractions (
                      city_id, name, latitude, longitude, attraction_type, source, metadata
                    )
                    values (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    [
                        city_id,
                        attraction.name,
                        attraction.latitude,
                        attraction.longitude,
                        attraction.category,
                        attraction.source,
                        json.dumps({"description": attraction.description}, default=_json_default),
                    ],
                )
        connection.commit()


def store_recommendation_score(
    *,
    city_id: str,
    travel_window_id: str,
    breakdown: RecommendationScoreBreakdown,
    final_score: int,
) -> None:
    if not database.is_database_configured():
        return
    database.execute(
        """
        insert into recommendation_scores (
          city_id, travel_window_id, climate_score, attraction_score,
          popularity_score, affordability_score, air_quality_score, final_score
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (city_id, travel_window_id) do update set
          climate_score = excluded.climate_score,
          attraction_score = excluded.attraction_score,
          popularity_score = excluded.popularity_score,
          affordability_score = excluded.affordability_score,
          air_quality_score = excluded.air_quality_score,
          final_score = excluded.final_score,
          calculated_at = now()
        """,
        [
            city_id,
            travel_window_id,
            breakdown.climate_score,
            breakdown.attraction_score,
            breakdown.popularity_score,
            breakdown.affordability_score,
            breakdown.air_quality_score,
            final_score,
        ],
    )
