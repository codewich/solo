from __future__ import annotations

import hashlib
import json
from uuid import uuid4
from datetime import UTC, datetime, timedelta
from typing import Any

from solo_api import database
from solo_api.cache import RedisJsonCache
from solo_api.cache import ATTRACTIONS_TTL_SECONDS
from solo_api.config import get_env
from solo_api.models import (
    AttractionSummary,
    ClimateSummary,
    Destination,
    Recommendation,
    RecommendationScoreBreakdown,
    TravelWindow,
)

REDIS_CACHE = RedisJsonCache(get_env("REDIS_URL") or get_env("REDIS_KV_URL"))


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def stable_cache_key(namespace: str, payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, default=_json_default)
    return f"{namespace}:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"


def is_provider_cache_disabled() -> bool:
    return (get_env("SOLO_DISABLE_PROVIDER_CACHE") or "").lower() in {"1", "true", "yes"}


def _slug(value: str) -> str:
    return "-".join(value.strip().casefold().replace("_", "-").split())


def city_provider_cache_key(
    *,
    city_id: str | None,
    city: str,
    country: str,
    namespace: str,
    version: str = "v1",
) -> str:
    if city_id:
        city_part = _slug(city_id)
    else:
        city_part = f"{_slug(city)}:{_slug(country)}"
    return f"city:{city_part}:{namespace}:{version}"


def get_api_cache(key: str) -> Any | None:
    if is_provider_cache_disabled():
        return None
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
    if is_provider_cache_disabled():
        return
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


def get_city(city_id: str) -> Destination | None:
    if not database.is_database_configured():
        return None

    row = database.fetch_one(
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
        where id = %s
        """,
        [city_id],
    )
    return Destination.model_validate(row) if row else None


def search_catalog_cities(query: str, limit: int = 5) -> list[Destination]:
    normalized_query = query.strip()
    if not database.is_database_configured() or len(normalized_query) < 2:
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
        where name ilike %s
        order by population desc nulls last
        limit %s
        """,
        [f"{normalized_query}%", limit],
    )
    return [Destination.model_validate(row) for row in rows]


def find_nearest_city(*, latitude: float, longitude: float) -> Destination | None:
    if not database.is_database_configured():
        return None

    row = database.fetch_one(
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
        order by geography(ST_MakePoint(longitude, latitude))
          <-> geography(ST_MakePoint(%s, %s))
        limit 1
        """,
        [longitude, latitude],
    )
    return Destination.model_validate(row) if row else None


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


def get_cached_attractions(
    *,
    city_id: str | None,
    city: str,
    country: str,
) -> list[AttractionSummary] | None:
    payload = get_api_cache(
        city_provider_cache_key(
            city_id=city_id,
            city=city,
            country=country,
            namespace="attractions",
            version="v2",
        )
    )
    if payload is None:
        return None
    if not isinstance(payload, list):
        return []
    return [AttractionSummary.model_validate(item) for item in payload]


def set_cached_attractions(
    *,
    city_id: str | None,
    city: str,
    country: str,
    attractions: list[AttractionSummary],
) -> None:
    set_api_cache(
        key=city_provider_cache_key(
            city_id=city_id,
            city=city,
            country=country,
            namespace="attractions",
            version="v2",
        ),
        payload=[attraction.model_dump(mode="json") for attraction in attractions],
        ttl_seconds=ATTRACTIONS_TTL_SECONDS,
        provider="attractions",
    )


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
          popularity_score, air_quality_score, final_score
        )
        values (%s, %s, %s, %s, %s, %s, %s)
        on conflict (city_id, travel_window_id) do update set
          climate_score = excluded.climate_score,
          attraction_score = excluded.attraction_score,
          popularity_score = excluded.popularity_score,
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
            breakdown.air_quality_score,
            final_score,
        ],
    )


def ensure_user(
    *,
    email: str | None,
    name: str | None = None,
    image_url: str | None = None,
    provider: str = "google",
    provider_subject: str | None = None,
) -> str:
    if not database.is_database_configured():
        return "demo-user"

    user_email = email or "demo@solo.local"
    subject = provider_subject or user_email
    existing = database.fetch_one(
        """
        select u.id
        from users u
        join user_auth_accounts a on a.user_id = u.id
        where a.provider = %s
          and a.provider_subject = %s
        """,
        [provider, subject],
    )
    if existing:
        return str(existing["id"])

    user_id = str(uuid4())
    with database.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into users (id, email, name, image_url)
                values (%s, %s, %s, %s)
                on conflict (email) do update set
                  name = coalesce(excluded.name, users.name),
                  image_url = coalesce(excluded.image_url, users.image_url),
                  updated_at = now()
                returning id
                """,
                [user_id, user_email, name, image_url],
            )
            user_id = str(cursor.fetchone()["id"])
            cursor.execute(
                """
                insert into user_auth_accounts (user_id, provider, provider_subject)
                values (%s, %s, %s)
                on conflict (provider, provider_subject) do nothing
                """,
                [user_id, provider, subject],
            )
        connection.commit()
    return user_id


def create_or_replace_recommendation_search(
    *,
    user_id: str,
    travel_window: TravelWindow,
    home_city_id: str,
    radius_km: int,
    min_population: int,
    candidate_limit: int,
    excluded_city_ids: list[str],
) -> str:
    if not database.is_database_configured():
        return f"memory:{user_id}:{travel_window.id}"

    search_id = str(uuid4())
    with database.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into travel_windows (id, user_id, label, start_date, end_date, status)
                values (%s, %s, %s, %s, %s, %s)
                on conflict (id) do update set
                  label = excluded.label,
                  start_date = excluded.start_date,
                  end_date = excluded.end_date,
                  status = excluded.status,
                  updated_at = now()
                """,
                [
                    travel_window.id,
                    user_id,
                    travel_window.label,
                    travel_window.start_date,
                    travel_window.end_date,
                    travel_window.status,
                ],
            )
            existing = cursor.execute(
                """
                select id, home_city_id, radius_km, min_population, candidate_limit
                from recommendation_searches
                where user_id = %s and travel_window_id = %s
                """,
                [user_id, travel_window.id],
            ).fetchone()
            should_replace_results = True
            if existing:
                search_id = str(existing["id"])
                existing_exclusions = cursor.execute(
                    """
                    select city_id
                    from recommendation_excluded_cities
                    where search_id = %s
                    """,
                    [search_id],
                ).fetchall()
                should_replace_results = (
                    existing["home_city_id"] != home_city_id
                    or existing["radius_km"] != radius_km
                    or existing["min_population"] != min_population
                    or existing["candidate_limit"] != candidate_limit
                    or {row["city_id"] for row in existing_exclusions} != set(excluded_city_ids)
                )
            cursor.execute(
                """
                insert into recommendation_searches (
                  id, user_id, travel_window_id, home_city_id, radius_km, min_population,
                  candidate_limit
                )
                values (%s, %s, %s, %s, %s, %s, %s)
                on conflict (user_id, travel_window_id) do update set
                  home_city_id = excluded.home_city_id,
                  radius_km = excluded.radius_km,
                  min_population = excluded.min_population,
                  candidate_limit = excluded.candidate_limit,
                  updated_at = now()
                """,
                [
                    search_id,
                    user_id,
                    travel_window.id,
                    home_city_id,
                    radius_km,
                    min_population,
                    candidate_limit,
                ],
            )
            cursor.execute("delete from recommendation_excluded_cities where search_id = %s", [search_id])
            if should_replace_results:
                cursor.execute("delete from recommendation_results where search_id = %s", [search_id])
            for city_id in excluded_city_ids:
                cursor.execute(
                    """
                    insert into recommendation_excluded_cities (search_id, city_id)
                    values (%s, %s)
                    on conflict do nothing
                    """,
                    [search_id, city_id],
                )
        connection.commit()
    return search_id


def get_recommendation_search(search_id: str) -> dict[str, Any] | None:
    if not database.is_database_configured():
        return None
    return database.fetch_one(
        """
        select
          s.id,
          s.user_id,
          s.travel_window_id,
          s.home_city_id,
          s.radius_km,
          s.min_population,
          s.candidate_limit,
          w.label,
          w.start_date,
          w.end_date,
          w.status,
          coalesce(array_agg(e.city_id) filter (where e.city_id is not null), '{}') as excluded_city_ids
        from recommendation_searches s
        join travel_windows w on w.id = s.travel_window_id
        left join recommendation_excluded_cities e on e.search_id = s.id
        where s.id = %s
        group by s.id, w.id
        """,
        [search_id],
    )


def store_recommendation_result(*, search_id: str, recommendation: Recommendation) -> None:
    if not database.is_database_configured() or search_id.startswith("memory:"):
        return
    database.execute(
        """
        insert into recommendation_results (search_id, city_id, score, payload)
        values (%s, %s, %s, %s::jsonb)
        on conflict (search_id, city_id) do update set
          score = excluded.score,
          payload = excluded.payload,
          updated_at = now()
        """,
        [
            search_id,
            recommendation.destination.id,
            recommendation.score,
            json.dumps(recommendation.model_dump(mode="json", by_alias=True), default=_json_default),
        ],
    )


def get_saved_recommendation_results(search_id: str) -> list[Recommendation]:
    if not database.is_database_configured() or search_id.startswith("memory:"):
        return []
    rows = database.fetch_all(
        """
        select payload
        from recommendation_results
        where search_id = %s
        order by score desc
        """,
        [search_id],
    )
    return [Recommendation.model_validate(row["payload"]) for row in rows]
