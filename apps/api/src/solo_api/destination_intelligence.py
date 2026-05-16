import hashlib
from collections.abc import Callable
from typing import TypeVar

from solo_api.attractions import AttractionLookupError, fetch_attractions
from solo_api.cache import TtlCache
from solo_api.cost_of_living import StaticCostOfLivingProvider
from solo_api.hotels import summarize_hotel_prices
from solo_api.models import (
    DestinationIntelligence,
    DestinationIntelligenceRequest,
    DestinationIntelligenceWarning,
)
from solo_api.weather import fetch_climate_summary

INTELLIGENCE_CACHE: TtlCache[DestinationIntelligence] = TtlCache(ttl_seconds=60 * 60 * 6)

CITY_CODES = {
    ("Lisbon", "Portugal"): "LIS",
    ("Porto", "Portugal"): "OPO",
    ("Seville", "Spain"): "SVQ",
    ("Copenhagen", "Denmark"): "CPH",
}

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
            request.destination_city,
            request.country,
            str(request.latitude),
            str(request.longitude),
            request.start_date.isoformat(),
            request.end_date.isoformat(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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

    city_code = CITY_CODES.get(
        (request.destination_city, request.country),
        request.destination_city[:3].upper(),
    )
    warnings: list[DestinationIntelligenceWarning] = []
    try:
        attractions = _run_step(
            step="attractions",
            service="OpenStreetMap/Wikipedia",
            action=lambda: fetch_attractions(
                latitude=request.latitude,
                longitude=request.longitude,
                city=request.destination_city,
            ),
        )
    except DestinationIntelligenceStepError as error:
        attractions = []
        warnings.append(_warning_from_error(error))

    intelligence = DestinationIntelligence(
        destination_city=request.destination_city,
        country=request.country,
        climate=_run_step(
            step="climate",
            service="Open-Meteo",
            action=lambda: fetch_climate_summary(
                latitude=request.latitude,
                longitude=request.longitude,
                start_date=request.start_date,
                end_date=request.end_date,
            ),
        ),
        attractions=attractions,
        hotels=_run_step(
            step="hotels",
            service="Amadeus",
            action=lambda: summarize_hotel_prices(
                city_code=city_code,
                check_in_date=request.start_date,
                check_out_date=request.end_date,
            ),
        ),
        cost_of_living=_run_step(
            step="cost_of_living",
            service="Cost of living seed",
            action=lambda: StaticCostOfLivingProvider().summary_for(
                city=request.destination_city,
                country=request.country,
            ),
        ),
        warnings=warnings,
    )
    if not warnings:
        INTELLIGENCE_CACHE.set(key, intelligence)
    return intelligence
