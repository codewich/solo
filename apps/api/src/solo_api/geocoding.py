import httpx

from solo_api.http import DEFAULT_TIMEOUT
from solo_api.models import CitySuggestion

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


def search_cities(query: str, count: int = 5) -> list[CitySuggestion]:
    normalized_query = query.strip()
    if len(normalized_query) < 2:
        return []

    response = httpx.get(
        GEOCODING_URL,
        params={
            "name": normalized_query,
            "count": count,
            "language": "en",
            "format": "json",
        },
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()

    suggestions: list[CitySuggestion] = []
    for item in payload.get("results", []):
        if not item.get("name") or not item.get("country"):
            continue
        suggestions.append(
            CitySuggestion(
                id=str(item["id"]),
                name=item["name"],
                country=item["country"],
                admin1=item.get("admin1"),
                latitude=item["latitude"],
                longitude=item["longitude"],
                timezone=item.get("timezone"),
            )
        )
    return suggestions
