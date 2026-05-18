from calendar import monthrange
from datetime import date
import logging

import httpx

from solo_api.http import DEFAULT_TIMEOUT
from solo_api.models import AirQualitySummary

logger = logging.getLogger(__name__)

OPEN_METEO_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
OPEN_METEO_AIR_QUALITY_HOURLY = "european_aqi,us_aqi,pm2_5,pm10,nitrogen_dioxide"


def air_quality_sample_year(today: date | None = None) -> int:
    return (today or date.today()).year - 1


def _average(values: list[float | int | None]) -> float | None:
    clean_values = [float(value) for value in values if isinstance(value, int | float)]
    if not clean_values:
        return None
    return round(sum(clean_values) / len(clean_values), 1)


def _summary(values: dict[str, float | None], *, year: int, month: int) -> str:
    parts = []
    if values.get("european_aqi") is not None:
        parts.append(f"European AQI {values['european_aqi']:.1f}")
    if values.get("us_aqi") is not None:
        parts.append(f"US AQI {values['us_aqi']:.1f}")
    if values.get("pm25") is not None:
        parts.append(f"PM2.5 {values['pm25']:.1f} ug/m3")
    if not parts:
        return "Open-Meteo air quality data is unavailable; ranking used a neutral fallback."
    return (
        f"Open-Meteo modeled air quality average for {year}-{month:02d}: "
        + ", ".join(parts)
        + "."
    )


def unavailable_air_quality_summary() -> AirQualitySummary:
    return AirQualitySummary(
        european_aqi=None,
        us_aqi=None,
        pm25=None,
        pm10=None,
        no2=None,
        summary="Open-Meteo air quality data is unavailable; ranking used a neutral fallback.",
        source="Open-Meteo",
        status="unavailable",
    )


def fetch_air_quality_summary(
    *,
    latitude: float,
    longitude: float,
    year: int,
    month: int,
) -> AirQualitySummary:
    try:
        last_day = monthrange(year, month)[1]
        response = httpx.get(
            OPEN_METEO_AIR_QUALITY_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "start_date": date(year, month, 1).isoformat(),
                "end_date": date(year, month, last_day).isoformat(),
                "hourly": OPEN_METEO_AIR_QUALITY_HOURLY,
                "timezone": "auto",
            },
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        hourly = response.json().get("hourly", {})
        values = {
            "european_aqi": _average(hourly.get("european_aqi", [])),
            "us_aqi": _average(hourly.get("us_aqi", [])),
            "pm25": _average(hourly.get("pm2_5", [])),
            "pm10": _average(hourly.get("pm10", [])),
            "no2": _average(hourly.get("nitrogen_dioxide", [])),
        }
        if all(value is None for value in values.values()):
            return unavailable_air_quality_summary()

        return AirQualitySummary(
            european_aqi=values["european_aqi"],
            us_aqi=values["us_aqi"],
            pm25=values["pm25"],
            pm10=values["pm10"],
            no2=values["no2"],
            summary=_summary(values, year=year, month=month),
            source="Open-Meteo",
            status="available",
        )
    except Exception as error:
        logger.exception("Error fetching Open-Meteo air quality: %s", error)
        return unavailable_air_quality_summary()
