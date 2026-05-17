from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import TypeAdapter

from solo_api import database
from solo_api.cache import RedisJsonCache
from solo_api.models import Destination, RecommendationScoreBreakdown

DESTINATION_LIST = TypeAdapter(list[Destination])
REDIS_CACHE = RedisJsonCache(os.getenv("REDIS_URL"))


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


def get_cached_cities(key: str) -> list[Destination] | None:
    payload = get_api_cache(key)
    if payload is None:
        return None
    return DESTINATION_LIST.validate_python(payload)


def set_cached_cities(key: str, destinations: list[Destination], ttl_seconds: int, provider: str) -> None:
    set_api_cache(
        key=key,
        payload=[destination.model_dump(mode="json") for destination in destinations],
        ttl_seconds=ttl_seconds,
        provider=provider,
    )


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
