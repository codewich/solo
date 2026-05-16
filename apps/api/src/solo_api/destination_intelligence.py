import hashlib

from solo_api.attractions import fetch_attractions
from solo_api.cache import TtlCache
from solo_api.cost_of_living import StaticCostOfLivingProvider
from solo_api.hotels import summarize_hotel_prices
from solo_api.models import DestinationIntelligence, DestinationIntelligenceRequest
from solo_api.weather import fetch_climate_summary

INTELLIGENCE_CACHE: TtlCache[DestinationIntelligence] = TtlCache(ttl_seconds=60 * 60 * 6)

CITY_CODES = {
    ("Lisbon", "Portugal"): "LIS",
    ("Porto", "Portugal"): "OPO",
    ("Seville", "Spain"): "SVQ",
    ("Copenhagen", "Denmark"): "CPH",
}


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
    intelligence = DestinationIntelligence(
        destination_city=request.destination_city,
        country=request.country,
        climate=fetch_climate_summary(
            latitude=request.latitude,
            longitude=request.longitude,
            start_date=request.start_date,
            end_date=request.end_date,
        ),
        attractions=fetch_attractions(
            latitude=request.latitude,
            longitude=request.longitude,
            city=request.destination_city,
        ),
        hotels=summarize_hotel_prices(
            city_code=city_code,
            check_in_date=request.start_date,
            check_out_date=request.end_date,
        ),
        cost_of_living=StaticCostOfLivingProvider().summary_for(
            city=request.destination_city,
            country=request.country,
        ),
    )
    INTELLIGENCE_CACHE.set(key, intelligence)
    return intelligence
