import os

import httpx

from solo_api.http import DEFAULT_TIMEOUT, USER_AGENT
from solo_api.models import AirQualitySummary

OPENAQ_BASE_URL = "https://api.openaq.org/v3"
OPENAQ_RADIUS_M = 25_000


def _headers() -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT}
    api_key = os.getenv("OPENAQ_API_KEY", "eb1b9cd8642b866d4b63d6f5a0aa1ee6df8bb116e0378737aa2f9f0e8dfd0820")
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _pollutant_values(results: list[dict], sensor_map: dict[int, str]) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in results:
        sensor_id = item.get("sensorsId")
        value = item.get("value")
        if sensor_id in sensor_map and isinstance(value, int | float):
            param_name = sensor_map[sensor_id]
            if param_name in {"pm25", "pm10", "no2"}:
                values[param_name] = float(value)
    return values


def _summary(values: dict[str, float]) -> str:
    parts = []
    if "pm25" in values:
        parts.append(f"PM2.5 {values['pm25']:.1f} ug/m3")
    if "pm10" in values:
        parts.append(f"PM10 {values['pm10']:.1f} ug/m3")
    if "no2" in values:
        parts.append(f"NO2 {values['no2']:.1f} ug/m3")
    if not parts:
        return "OpenAQ has a nearby station but no PM2.5, PM10, or NO2 reading."
    return "Latest nearby OpenAQ readings: " + ", ".join(parts) + "."


def unavailable_air_quality_summary() -> AirQualitySummary:
    return AirQualitySummary(
        pm25=None,
        pm10=None,
        no2=None,
        summary="Air quality data is unavailable; ranking used a neutral fallback.",
        source="OpenAQ",
        status="unavailable",
    )


def fetch_air_quality_summary(latitude: float, longitude: float) -> AirQualitySummary:
    try:
        locations_response = httpx.get(
            f"{OPENAQ_BASE_URL}/locations",
            params={
                "coordinates": f"{latitude:.4f},{longitude:.4f}",
                "radius": OPENAQ_RADIUS_M,
                "limit": 1,
            },
            headers=_headers(),
            timeout=DEFAULT_TIMEOUT,
        )
        locations_response.raise_for_status()
        locations = locations_response.json().get("results", [])
        if not locations:
            return unavailable_air_quality_summary()

        location_id = locations[0].get("id")
        if not isinstance(location_id, int):
            return unavailable_air_quality_summary()

        # Get sensor metadata to map sensor IDs to parameter names
        sensors_response = httpx.get(
            f"{OPENAQ_BASE_URL}/locations/{location_id}/sensors",
            headers=_headers(),
            timeout=DEFAULT_TIMEOUT,
        )
        sensors_response.raise_for_status()
        sensor_map = {}
        for sensor in sensors_response.json().get("results", []):
            sensor_id = sensor.get("id")
            param = sensor.get("parameter", {})
            param_name = param.get("name")
            if isinstance(sensor_id, int) and param_name:
                sensor_map[sensor_id] = param_name

        # Get latest readings
        latest_response = httpx.get(
            f"{OPENAQ_BASE_URL}/locations/{location_id}/latest",
            headers=_headers(),
            timeout=DEFAULT_TIMEOUT,
        )
        latest_response.raise_for_status()
        values = _pollutant_values(latest_response.json().get("results", []), sensor_map)
        if not values:
            return unavailable_air_quality_summary()

        return AirQualitySummary(
            pm25=values.get("pm25"),
            pm10=values.get("pm10"),
            no2=values.get("no2"),
            summary=_summary(values),
            source="OpenAQ",
            status="available",
        )
    except Exception:
        return unavailable_air_quality_summary()
