import hashlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from solo_api.attraction_service import resolve_city_attractions
from solo_api.air_quality import (
    air_quality_sample_year,
    fetch_air_quality_summary,
    unavailable_air_quality_summary,
)
from solo_api.attractions import fetch_wikimedia_image, fetch_wikimedia_summary
from solo_api.cache import TtlCache
from solo_api.models import AirQualitySummary, ClimateSummary, Destination, TravelWindow
from solo_api.storage import (
    get_air_quality_normal,
    get_climate_normal,
    store_air_quality_normal,
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
    warnings: list[str]


SIGNAL_CACHE_TTL_SECONDS = 60 * 60 * 6
SIGNAL_CACHE_VERSION = "v4"
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
            SIGNAL_CACHE_VERSION,
            destination.id,
            destination.city,
            destination.country,
            window.start_date.isoformat(),
            window.end_date.isoformat(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def dominant_month(window: TravelWindow) -> int:
    coverage: dict[int, int] = defaultdict(int)
    last_seen: dict[int, date] = {}
    current = window.start_date
    while current <= window.end_date:
        coverage[current.month] += 1
        last_seen[current.month] = current
        current += timedelta(days=1)
    return max(coverage, key=lambda month: (coverage[month], last_seen[month]))


def get_destination_signals(destination: Destination, window: TravelWindow) -> DestinationSignals:
    key = _cache_key(destination, window)
    cached = SIGNAL_CACHE.get(key)
    if cached is not None:
        return cached

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
        attractions = resolve_city_attractions(
            city_id=destination.id,
            city=destination.city,
            country=destination.country,
            latitude=destination.latitude,
            longitude=destination.longitude,
            radius_m=2500,
        )
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
        air_quality_year = air_quality_sample_year()
        air_quality = get_air_quality_normal(
            city_id=destination.id,
            year=air_quality_year,
            month=climate_month,
        )
        if air_quality is None:
            air_quality = fetch_air_quality_summary(
                latitude=destination.latitude,
                longitude=destination.longitude,
                year=air_quality_year,
                month=climate_month,
            )
            store_air_quality_normal(
                city_id=destination.id,
                year=air_quality_year,
                month=climate_month,
                air_quality=air_quality,
            )
        if air_quality.status == "unavailable":
            warnings.append("Open-Meteo air quality unavailable; air quality score used a neutral fallback.")
    except Exception:
        air_quality = unavailable_air_quality_summary()
        warnings.append("Open-Meteo air quality unavailable; air quality score used a neutral fallback.")

    signals = DestinationSignals(
        climate=climate,
        attraction_count=attraction_count,
        summary=summary,
        image_url=image_url,
        air_quality=air_quality,
        warnings=warnings,
    )
    SIGNAL_CACHE.set(key, signals)
    return signals
