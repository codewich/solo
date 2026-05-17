import hashlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from solo_api.air_quality import fetch_air_quality_summary, unavailable_air_quality_summary
from solo_api.attractions import fetch_attractions, fetch_wikimedia_image, fetch_wikimedia_summary
from solo_api.cache import TtlCache
from solo_api.cost_of_living import unavailable_cost_of_living_summary
from solo_api.models import AirQualitySummary, ClimateSummary, CostOfLivingSummary, Destination, TravelWindow
from solo_api.storage import (
    get_api_cache,
    get_climate_normal,
    get_stored_attractions,
    set_api_cache,
    store_attractions,
    store_climate_normal,
)
from solo_api.weather import fetch_month_climate_summary


@dataclass(frozen=True)
class DestinationSignals:
    climate: ClimateSummary
    attraction_count: int
    summary: str | None
    image_url: str | None
    air_quality: AirQualitySummary
    cost_of_living: CostOfLivingSummary
    warnings: list[str]


SIGNAL_CACHE_TTL_SECONDS = 60 * 60 * 6
SIGNAL_CACHE: TtlCache[DestinationSignals] = TtlCache(ttl_seconds=SIGNAL_CACHE_TTL_SECONDS)


def _empty_climate_summary() -> ClimateSummary:
    return ClimateSummary(
        average_temperature_c=None,
        precipitation_mm=None,
        sunshine_hours=None,
        summary="Climate data is unavailable; ranking used destination seed context.",
    )


def _cache_key(destination: Destination, window: TravelWindow) -> str:
    raw = "|".join(
        [
            destination.id,
            destination.city,
            destination.country,
            window.start_date.isoformat(),
            window.end_date.isoformat(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _shared_cache_key(local_key: str) -> str:
    return f"destination_signals:{local_key}"


def dominant_month(window: TravelWindow) -> int:
    coverage: dict[int, int] = defaultdict(int)
    last_seen: dict[int, date] = {}
    current = window.start_date
    while current <= window.end_date:
        coverage[current.month] += 1
        last_seen[current.month] = current
        current += timedelta(days=1)
    return max(coverage, key=lambda month: (coverage[month], last_seen[month]))


def _signals_to_payload(signals: DestinationSignals) -> dict:
    return {
        "climate": signals.climate.model_dump(mode="json"),
        "attraction_count": signals.attraction_count,
        "summary": signals.summary,
        "image_url": signals.image_url,
        "air_quality": signals.air_quality.model_dump(mode="json"),
        "cost_of_living": signals.cost_of_living.model_dump(mode="json"),
        "warnings": signals.warnings,
    }


def _signals_from_payload(payload: dict) -> DestinationSignals:
    return DestinationSignals(
        climate=ClimateSummary.model_validate(payload["climate"]),
        attraction_count=payload["attraction_count"],
        summary=payload.get("summary"),
        image_url=payload.get("image_url"),
        air_quality=AirQualitySummary.model_validate(payload["air_quality"]),
        cost_of_living=CostOfLivingSummary.model_validate(payload["cost_of_living"]),
        warnings=list(payload.get("warnings", [])),
    )


def get_destination_signals(destination: Destination, window: TravelWindow) -> DestinationSignals:
    key = _cache_key(destination, window)
    cached = SIGNAL_CACHE.get(key)
    if cached is not None:
        return cached

    shared_key = _shared_cache_key(key)
    cached_payload = get_api_cache(shared_key)
    if cached_payload is not None:
        signals = _signals_from_payload(cached_payload)
        SIGNAL_CACHE.set(key, signals)
        return signals

    warnings: list[str] = []
    climate_month = dominant_month(window)

    try:
        climate = get_climate_normal(city_id=destination.id, month=climate_month)
        if climate is None:
            climate = fetch_month_climate_summary(
                latitude=destination.latitude,
                longitude=destination.longitude,
                year=window.start_date.year,
                month=climate_month,
            )
            store_climate_normal(
                city_id=destination.id,
                month=climate_month,
                climate=climate,
                source=climate.source,
            )
    except Exception:
        climate = _empty_climate_summary()
        warnings.append("Open-Meteo unavailable; climate score used a neutral fallback.")

    try:
        attractions = get_stored_attractions(destination.id)
        if not attractions:
            attractions = fetch_attractions(
                latitude=destination.latitude,
                longitude=destination.longitude,
                city=destination.city,
                radius_m=2500,
            )
            store_attractions(city_id=destination.id, attractions=attractions)
        attraction_count = len(attractions)
    except Exception:
        attraction_count = 0
        warnings.append("OpenStreetMap unavailable; attraction score used a neutral fallback.")

    try:
        summary = fetch_wikimedia_summary(destination.city)
        if summary is None:
            warnings.append("Wikimedia unavailable; popularity score used population only.")
    except Exception:
        summary = None
        warnings.append("Wikimedia unavailable; popularity score used population only.")

    try:
        image_url = fetch_wikimedia_image(destination.city)
    except Exception:
        image_url = None
        warnings.append("Wikimedia unavailable; city image was omitted.")

    try:
        air_quality = fetch_air_quality_summary(
            latitude=destination.latitude,
            longitude=destination.longitude,
        )
        if air_quality.status == "unavailable":
            warnings.append("OpenAQ unavailable; air quality score used a neutral fallback.")
    except Exception:
        air_quality = unavailable_air_quality_summary()
        warnings.append("OpenAQ unavailable; air quality score used a neutral fallback.")

    cost_of_living = unavailable_cost_of_living_summary(destination.city)

    signals = DestinationSignals(
        climate=climate,
        attraction_count=attraction_count,
        summary=summary,
        image_url=image_url,
        air_quality=air_quality,
        cost_of_living=cost_of_living,
        warnings=warnings,
    )
    SIGNAL_CACHE.set(key, signals)
    set_api_cache(
        key=shared_key,
        payload=_signals_to_payload(signals),
        ttl_seconds=SIGNAL_CACHE_TTL_SECONDS,
        provider="destination_signals",
    )
    return signals
