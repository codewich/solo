import os
from datetime import date
from statistics import median

import httpx

from solo_api.http import DEFAULT_TIMEOUT
from solo_api.models import HotelPriceSummary

AMADEUS_TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_HOTEL_OFFERS_URL = "https://test.api.amadeus.com/v3/shopping/hotel-offers"


def _credentials() -> tuple[str, str] | None:
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    return client_id, client_secret


def _access_token(client_id: str, client_secret: str) -> str:
    response = httpx.post(
        AMADEUS_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def summarize_hotel_prices(
    city_code: str,
    check_in_date: date,
    check_out_date: date,
) -> HotelPriceSummary:
    credentials = _credentials()
    if credentials is None:
        return HotelPriceSummary(
            average_nightly_price=None,
            median_nightly_price=None,
            currency=None,
            sample_size=0,
            status="unavailable",
        )

    token = _access_token(*credentials)
    response = httpx.get(
        AMADEUS_HOTEL_OFFERS_URL,
        params={
            "cityCode": city_code,
            "checkInDate": check_in_date.isoformat(),
            "checkOutDate": check_out_date.isoformat(),
            "adults": 1,
            "roomQuantity": 1,
            "bestRateOnly": "true",
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()

    prices: list[float] = []
    currency: str | None = None
    for item in response.json().get("data", []):
        for offer in item.get("offers", []):
            price = offer.get("price", {})
            total = price.get("total")
            if total is None:
                continue
            currency = currency or price.get("currency")
            prices.append(float(total))

    if not prices:
        return HotelPriceSummary(
            average_nightly_price=None,
            median_nightly_price=None,
            currency=currency,
            sample_size=0,
            status="unavailable",
        )

    nights = max(1, (check_out_date - check_in_date).days)
    nightly_prices = [price / nights for price in prices]
    return HotelPriceSummary(
        average_nightly_price=round(sum(nightly_prices) / len(nightly_prices), 2),
        median_nightly_price=round(median(nightly_prices), 2),
        currency=currency,
        sample_size=len(nightly_prices),
    )
