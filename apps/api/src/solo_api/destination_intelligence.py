import hashlib
from collections import defaultdict
from collections.abc import Callable
from datetime import date, timedelta
from typing import TypeVar

from solo_api.attraction_service import resolve_city_attractions
from solo_api.attractions import AttractionLookupError
from solo_api.cache import TtlCache
from solo_api.models import (
    DestinationIntelligence,
    DestinationIntelligenceRequest,
    DestinationIntelligenceWarning,
)
from solo_api.storage import (
    get_climate_normal,
    store_climate_normal,
)
from solo_api.weather import fetch_month_climate_summary

INTELLIGENCE_CACHE_TTL_SECONDS = 60 * 60 * 6
INTELLIGENCE_CACHE_VERSION = "v3"
INTELLIGENCE_CACHE: TtlCache[DestinationIntelligence] = TtlCache(
    ttl_seconds=INTELLIGENCE_CACHE_TTL_SECONDS
)

T = TypeVar("T")


class DestinationIntelligenceStepError(Exception):
    def __init__(self, *, step: str, service: str, original_error: Exception):
        self.step = step
        self.service = (
            original_error.service if isinstance(original_error, AttractionLookupError) else service
        )
        self.original_error = original_error
        self.message = f"{self.service} failed during {step} lookup: {original_error}"
        super().__init__(self.message)


def _cache_key(request: DestinationIntelligenceRequest) -> str:
    raw = "|".join(
        [
            INTELLIGENCE_CACHE_VERSION,
            request.destination_city,
            request.country,
            str(request.latitude),
            str(request.longitude),
            request.start_date.isoformat(),
            request.end_date.isoformat(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dominant_month(start_date: date, end_date: date) -> int:
    coverage: dict[int, int] = defaultdict(int)
    last_seen: dict[int, date] = {}
    current = start_date
    while current <= end_date:
        coverage[current.month] += 1
        last_seen[current.month] = current
        current += timedelta(days=1)
    return max(coverage, key=lambda month: (coverage[month], last_seen[month]))


def _run_step(*, step: str, service: str, action: Callable[[], T]) -> T:
    try:
        return action()
    except Exception as error:
        raise DestinationIntelligenceStepError(
            step=step,
            service=service,
            original_error=error,
        ) from error


def _warning_from_error(error: DestinationIntelligenceStepError) -> DestinationIntelligenceWarning:
    return DestinationIntelligenceWarning(
        step=error.step,
        service=error.service,
        message=error.message,
    )


def build_destination_intelligence(
    request: DestinationIntelligenceRequest,
) -> DestinationIntelligence:
    key = _cache_key(request)
    cached = INTELLIGENCE_CACHE.get(key)
    if cached is not None:
        return cached

    warnings: list[DestinationIntelligenceWarning] = []
    climate_month = _dominant_month(request.start_date, request.end_date)
    try:
        attractions = _run_step(
            step="attractions",
            service="OpenStreetMap/Wikipedia/Wikidata",
            action=lambda: resolve_city_attractions(
                city_id=request.city_id,
                city=request.destination_city,
                country=request.country,
                latitude=request.latitude,
                longitude=request.longitude,
            ),
        )
    except DestinationIntelligenceStepError as error:
        attractions = []
        warnings.append(_warning_from_error(error))

    climate = (
        get_climate_normal(city_id=request.city_id, month=climate_month)
        if request.city_id
        else None
    )
    if climate is None:
        climate = _run_step(
            step="climate",
            service="Open-Meteo",
            action=lambda: fetch_month_climate_summary(
                latitude=request.latitude,
                longitude=request.longitude,
                year=request.start_date.year,
                month=climate_month,
            ),
        )
        if request.city_id:
            store_climate_normal(
                city_id=request.city_id,
                month=climate_month,
                climate=climate,
                source=climate.source,
            )

    intelligence = DestinationIntelligence(
        destination_city=request.destination_city,
        country=request.country,
        climate=climate,
        attractions=attractions,
        warnings=warnings,
    )
    if not warnings:
        INTELLIGENCE_CACHE.set(key, intelligence)
    return intelligence
