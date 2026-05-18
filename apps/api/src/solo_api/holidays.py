from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from solo_api.config import get_env
from solo_api.http import DEFAULT_TIMEOUT, USER_AGENT
from solo_api.models import HolidayRegion, PublicHoliday
from solo_api.storage import (
    get_cached_holiday_regions,
    get_holiday_region_cache_status,
    get_cached_public_holidays,
    set_holiday_region_cache_status,
    store_holiday_regions,
    store_public_holidays,
)

CALENDARIFIC_BASE_URL = "https://calendarific.com/api/v2"
PUBLIC_HOLIDAY_TYPES = {
    "national",
    "national holiday",
    "local",
    "local holiday",
    "public",
    "public holiday",
    "bank holiday",
}

STATIC_REGION_OPTIONS: dict[str, list[HolidayRegion]] = {
    "GB": [
        HolidayRegion(country_code="GB", region_code="gb-eng", name="England"),
        HolidayRegion(country_code="GB", region_code="gb-wls", name="Wales"),
        HolidayRegion(country_code="GB", region_code="gb-sct", name="Scotland"),
        HolidayRegion(country_code="GB", region_code="gb-nir", name="Northern Ireland"),
    ],
}


class CalendarificProviderError(RuntimeError):
    pass


def _api_key() -> str | None:
    return get_env("CALENDARIFIC_API_KEY")


def _headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT}


def _calendarific_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    api_key = _api_key()
    if not api_key:
        raise CalendarificProviderError("CALENDARIFIC_API_KEY is not configured.")
    try:
        response = httpx.get(
            f"{CALENDARIFIC_BASE_URL}/{path}",
            params={**params, "api_key": api_key, "debug": True},
            headers=_headers(),
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as error:
        raise CalendarificProviderError(f"Calendarific request failed: {error}") from error
    except ValueError as error:
        raise CalendarificProviderError("Calendarific returned an invalid JSON response.") from error

    meta = payload.get("meta", {})
    code = meta.get("code")
    if code not in {200, None}:
        error_detail = meta.get("error_detail") or meta.get("error_type") or "unknown error"
        raise CalendarificProviderError(f"Calendarific returned {code}: {error_detail}")
    return payload


def get_holiday_regions(country: str) -> list[HolidayRegion]:
    country_code = country.upper()
    cached = get_cached_holiday_regions(country_code)
    if cached:
        return cached
    if get_holiday_region_cache_status(country_code) == "empty":
        return []

    try:
        payload = _calendarific_get("countries", {})
        regions = _regions_from_calendarific_payload(country_code, payload)
    except CalendarificProviderError:
        regions = STATIC_REGION_OPTIONS.get(country_code, [])
        payload = {"source": "static-region-options"}
        if not regions:
            set_holiday_region_cache_status(country_code, "failed", "Calendarific region metadata unavailable.")
            raise
    store_holiday_regions(country_code, regions, payload)
    return regions


def get_bank_holidays(
    country: str,
    year: int,
    region: str | None = None,
) -> list[PublicHoliday]:
    country_code = country.upper()
    cached = get_cached_public_holidays(
        country_code=country_code,
        year=year,
        region_code=region,
    )
    if cached:
        return cached

    payload = _calendarific_get(
        "holidays",
        {
            "country": country_code,
            "year": year,
            "type": "national",
            **({"location": region} if region else {}),
        },
    )
    holidays = _holidays_from_calendarific_payload(country_code, year, region, payload)
    store_public_holidays(
        country_code=country_code,
        year=year,
        region_code=region,
        holidays=holidays,
    )
    return holidays


def _regions_from_calendarific_payload(
    country_code: str,
    payload: dict[str, Any] | None,
) -> list[HolidayRegion]:
    countries = payload.get("response", {}).get("countries", []) if payload else []
    for country in countries:
        if str(country.get("iso-3166") or country.get("id") or "").upper() != country_code:
            continue
        raw_regions = (
            country.get("states")
            or country.get("regions")
            or country.get("locations")
            or []
        )
        regions = []
        if isinstance(raw_regions, dict):
            raw_regions = raw_regions.values()
        for item in raw_regions:
            if not isinstance(item, dict):
                continue
            region_code = item.get("iso-3166") or item.get("id") or item.get("code")
            name = item.get("name") or item.get("state") or item.get("region")
            if region_code and name:
                regions.append(
                    HolidayRegion(
                        country_code=country_code,
                        region_code=str(region_code).lower(),
                        name=str(name),
                    )
                )
        return regions
    return []


def _holidays_from_calendarific_payload(
    country_code: str,
    year: int,
    region_code: str | None,
    payload: dict[str, Any],
) -> list[PublicHoliday]:
    raw_holidays = payload.get("response", {}).get("holidays", [])
    holidays = []
    for item in raw_holidays:
        if not isinstance(item, dict):
            continue
        holiday_types = {str(value).lower() for value in item.get("type", [])}
        if holiday_types and holiday_types.isdisjoint(PUBLIC_HOLIDAY_TYPES):
            continue
        iso_date = item.get("date", {}).get("iso")
        name = item.get("name")
        if not iso_date or not name:
            continue
        try:
            holiday_date = date.fromisoformat(str(iso_date)[:10])
        except ValueError:
            continue
        if holiday_date.year != year:
            continue
        holidays.append(
            PublicHoliday(
                date=holiday_date,
                name=str(name),
                country_code=country_code,
                region_code=region_code,
                type=", ".join(sorted(holiday_types)) if holiday_types else None,
            )
        )
    return holidays
