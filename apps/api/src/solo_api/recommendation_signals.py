import hashlib
from dataclasses import dataclass

from solo_api.air_quality import fetch_air_quality_summary, unavailable_air_quality_summary
from solo_api.attractions import count_attractions, fetch_wikimedia_image, fetch_wikimedia_summary
from solo_api.cache import TtlCache
from solo_api.cost_of_living import unavailable_cost_of_living_summary
from solo_api.models import AirQualitySummary, ClimateSummary, CostOfLivingSummary, Destination, TravelWindow
from solo_api.weather import fetch_climate_summary


@dataclass(frozen=True)
class DestinationSignals:
    climate: ClimateSummary
    attraction_count: int
    summary: str | None
    image_url: str | None
    air_quality: AirQualitySummary
    cost_of_living: CostOfLivingSummary
    warnings: list[str]


SIGNAL_CACHE: TtlCache[DestinationSignals] = TtlCache(ttl_seconds=60 * 60 * 6)


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


def get_destination_signals(destination: Destination, window: TravelWindow) -> DestinationSignals:
    key = _cache_key(destination, window)
    cached = SIGNAL_CACHE.get(key)
    if cached is not None:
        return cached

    warnings: list[str] = []

    try:
        climate = fetch_climate_summary(
            latitude=destination.latitude,
            longitude=destination.longitude,
            start_date=window.start_date,
            end_date=window.end_date,
        )
    except Exception:
        climate = _empty_climate_summary()
        warnings.append("Open-Meteo unavailable; climate score used a neutral fallback.")

    try:
        attraction_count = count_attractions(
            latitude=destination.latitude,
            longitude=destination.longitude,
            radius_m=2500,
        )
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
    return signals
