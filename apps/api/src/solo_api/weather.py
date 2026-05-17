from calendar import monthrange
from datetime import date

import httpx

from solo_api.http import DEFAULT_TIMEOUT
from solo_api.models import ClimateSummary

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def _average(values: list[float | None]) -> float | None:
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return None
    return round(sum(clean_values) / len(clean_values), 1)


def _sum(values: list[float | None], divisor: float = 1.0) -> float | None:
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return None
    return round(sum(clean_values) / divisor, 1)


def _subtract_year(value: date) -> date:
    try:
        return value.replace(year=value.year - 1)
    except ValueError:
        return value.replace(year=value.year - 1, day=28)


def historical_archive_window(
    start_date: date,
    end_date: date,
    latest_available: date | None = None,
) -> tuple[date, date]:
    latest = latest_available or date.today()
    archive_start = start_date
    archive_end = end_date

    while archive_end > latest:
        archive_start = _subtract_year(archive_start)
        archive_end = _subtract_year(archive_end)

    return archive_start, archive_end


def fetch_climate_summary(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> ClimateSummary:
    archive_start_date, archive_end_date = historical_archive_window(
        start_date=start_date,
        end_date=end_date,
    )
    response = httpx.get(
        OPEN_METEO_ARCHIVE_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "start_date": archive_start_date.isoformat(),
            "end_date": archive_end_date.isoformat(),
            "daily": (
                "temperature_2m_mean,temperature_2m_min,temperature_2m_max,"
                "precipitation_sum,sunshine_duration"
            ),
            "timezone": "auto",
        },
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    daily = response.json().get("daily", {})

    average_temperature = _average(daily.get("temperature_2m_mean", []))
    average_temperature_min = _average(daily.get("temperature_2m_min", []))
    average_temperature_max = _average(daily.get("temperature_2m_max", []))
    precipitation = _sum(daily.get("precipitation_sum", []))
    sunshine_hours = _sum(daily.get("sunshine_duration", []), divisor=3600.0)
    summary = "Historical climate data is available for this travel window."
    if average_temperature is not None:
        summary = f"Average historical temperature is about {average_temperature}C for this window."

    return ClimateSummary(
        average_temperature_c=average_temperature,
        average_temperature_min_c=average_temperature_min,
        average_temperature_max_c=average_temperature_max,
        precipitation_mm=precipitation,
        sunshine_hours=sunshine_hours,
        summary=summary,
    )


def fetch_month_climate_summary(
    latitude: float,
    longitude: float,
    year: int,
    month: int,
) -> ClimateSummary:
    last_day = monthrange(year, month)[1]
    return fetch_climate_summary(
        latitude=latitude,
        longitude=longitude,
        start_date=date(year, month, 1),
        end_date=date(year, month, last_day),
    )
