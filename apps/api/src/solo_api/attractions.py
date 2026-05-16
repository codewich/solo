import httpx
import overpass

from solo_api.http import DEFAULT_TIMEOUT, USER_AGENT
from solo_api.models import AttractionSummary

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
WIKIMEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
ATTRACTION_TIMEOUT = httpx.Timeout(12.0, connect=4.0)
OVERPASS_TIMEOUT_SECONDS = 12


class AttractionLookupError(Exception):
    def __init__(self, *, service: str, message: str, original_error: Exception):
        self.service = service
        self.original_error = original_error
        super().__init__(message)


def _category(tags: dict) -> str:
    for key in ("historic", "tourism", "amenity", "religion"):
        value = tags.get(key)
        if value:
            return str(value)
    return "point of interest"


def fetch_wikimedia_summary(city: str) -> str | None:
    payload = fetch_wikimedia_page_summary(city)
    extract = payload.get("extract")
    return extract if isinstance(extract, str) and extract else None


def fetch_wikimedia_image(city: str) -> str | None:
    payload = fetch_wikimedia_page_summary(city)
    original_image = payload.get("originalimage")
    if isinstance(original_image, dict) and isinstance(original_image.get("source"), str):
        return original_image["source"]
    thumbnail = payload.get("thumbnail")
    if isinstance(thumbnail, dict) and isinstance(thumbnail.get("source"), str):
        return thumbnail["source"]
    return None


def fetch_wikimedia_page_summary(city: str) -> dict:
    try:
        response = httpx.get(
            WIKIMEDIA_SUMMARY_URL.format(title=city.replace(" ", "_")),
            headers={"User-Agent": USER_AGENT},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return {}

    payload = response.json()
    return payload if isinstance(payload, dict) else {}


def _overpass_query(
    *,
    latitude: float,
    longitude: float,
    radius_m: int,
    include_historic: bool,
) -> str:
    historic_queries = (
        f"""
      node(around:{radius_m},{latitude},{longitude})["historic"~"castle|monument|archaeological_site"]["name"];
      way(around:{radius_m},{latitude},{longitude})["historic"~"castle|monument|archaeological_site"]["name"];"""
        if include_historic
        else ""
    )
    return f"""
    [out:json][timeout:12];
    (
      node(around:{radius_m},{latitude},{longitude})["tourism"~"museum|attraction|viewpoint|gallery"]["name"];
      way(around:{radius_m},{latitude},{longitude})["tourism"~"museum|attraction|viewpoint|gallery"]["name"];{historic_queries}
    );
    out center tags qt 12;
    """


def _post_overpass_query(query: str) -> httpx.Response:
    return httpx.post(
        OVERPASS_URL,
        data={"data": query},
        headers={"User-Agent": USER_AGENT},
        timeout=ATTRACTION_TIMEOUT,
    )


def _overpass_api() -> overpass.API:
    return overpass.API(user_agent=USER_AGENT, timeout=OVERPASS_TIMEOUT_SECONDS)


def count_attractions(
    latitude: float,
    longitude: float,
    radius_m: int = 2500,
) -> int:
    query = _overpass_query(
        latitude=latitude,
        longitude=longitude,
        radius_m=radius_m,
        include_historic=True,
    )
    try:
        response = _overpass_api().get(query, responseformat="json", build=False)
    except overpass.TimeoutError:
        try:
            response = _overpass_api().get(
                _overpass_query(
                    latitude=latitude,
                    longitude=longitude,
                    radius_m=radius_m,
                    include_historic=False,
                ),
                responseformat="json",
                build=False,
            )
        except Exception as retry_error:
            raise AttractionLookupError(
                service="OpenStreetMap",
                message="OpenStreetMap timed out while counting nearby attractions.",
                original_error=retry_error,
            ) from retry_error
    except Exception as error:
        raise AttractionLookupError(
            service="OpenStreetMap",
            message="OpenStreetMap failed while counting nearby attractions.",
            original_error=error,
        ) from error

    if not isinstance(response, dict):
        return 0
    if isinstance(response.get("features"), list):
        return len(response["features"])
    if isinstance(response.get("elements"), list):
        return len(response["elements"])
    return 0


def fetch_attractions(
    latitude: float,
    longitude: float,
    city: str | None = None,
    radius_m: int = 6000,
) -> list[AttractionSummary]:
    query = _overpass_query(
        latitude=latitude,
        longitude=longitude,
        radius_m=radius_m,
        include_historic=True,
    )
    try:
        response = _post_overpass_query(query)
        response.raise_for_status()
    except httpx.TimeoutException:
        try:
            response = _post_overpass_query(
                _overpass_query(
                    latitude=latitude,
                    longitude=longitude,
                    radius_m=radius_m,
                    include_historic=False,
                )
            )
            response.raise_for_status()
        except httpx.TimeoutException as retry_error:
            raise AttractionLookupError(
                service="OpenStreetMap",
                message="OpenStreetMap timed out while querying nearby attractions.",
                original_error=retry_error,
            ) from retry_error
        except httpx.HTTPStatusError as retry_error:
            status_code = retry_error.response.status_code
            raise AttractionLookupError(
                service="OpenStreetMap",
                message=(
                    f"OpenStreetMap returned HTTP {status_code} "
                    "while querying nearby attractions."
                ),
                original_error=retry_error,
            ) from retry_error
        except httpx.HTTPError as retry_error:
            raise AttractionLookupError(
                service="OpenStreetMap",
                message="OpenStreetMap failed while querying nearby attractions.",
                original_error=retry_error,
            ) from retry_error
    except httpx.HTTPStatusError as error:
        status_code = error.response.status_code
        raise AttractionLookupError(
            service="OpenStreetMap",
            message=f"OpenStreetMap returned HTTP {status_code} while querying nearby attractions.",
            original_error=error,
        ) from error
    except httpx.HTTPError as error:
        raise AttractionLookupError(
            service="OpenStreetMap",
            message="OpenStreetMap failed while querying nearby attractions.",
            original_error=error,
        ) from error

    destination_summary = fetch_wikimedia_summary(city) if city else None
    attractions: list[AttractionSummary] = []
    seen_names: set[str] = set()
    for element in response.json().get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name")
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        center = element.get("center", {})
        attractions.append(
            AttractionSummary(
                name=name,
                category=_category(tags),
                latitude=element.get("lat", center.get("lat")),
                longitude=element.get("lon", center.get("lon")),
                description=destination_summary if not attractions else None,
                source="OpenStreetMap",
            )
        )
        if len(attractions) == 8:
            break

    return attractions
