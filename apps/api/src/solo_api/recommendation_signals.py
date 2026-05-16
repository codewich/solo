import hashlib
from dataclasses import dataclass

from solo_api.attractions import fetch_attractions, fetch_wikimedia_summary
from solo_api.cache import TtlCache
from solo_api.cost_of_living import StaticCostOfLivingProvider
from solo_api.models import AttractionSummary, ClimateSummary, CostOfLivingSummary, Destination, TravelWindow
from solo_api.weather import fetch_climate_summary


@dataclass(frozen=True)
class DestinationSignals:
    climate: ClimateSummary
    attractions: list[AttractionSummary]
    summary: str | None
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
        attractions = fetch_attractions(
            latitude=destination.latitude,
            longitude=destination.longitude,
            city=None,
            radius_m=2500,
        )
    except Exception:
        attractions = []
        warnings.append("OpenStreetMap unavailable; attraction score used seed tags only.")

    try:
        summary = fetch_wikimedia_summary(destination.city)
        if summary is None:
            warnings.append("Wikimedia unavailable; popularity score used seed tags only.")
    except Exception:
        summary = None
        warnings.append("Wikimedia unavailable; popularity score used seed tags only.")

    cost_of_living = StaticCostOfLivingProvider().summary_for(
        city=destination.city,
        country=destination.country,
    )

    signals = DestinationSignals(
        climate=climate,
        attractions=attractions,
        summary=summary,
        cost_of_living=cost_of_living,
        warnings=warnings,
    )
    SIGNAL_CACHE.set(key, signals)
    return signals
