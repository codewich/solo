import httpx

from solo_api.http import DEFAULT_TIMEOUT, USER_AGENT
from solo_api.models import AttractionSummary

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
WIKIMEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"


def _category(tags: dict) -> str:
    for key in ("historic", "tourism", "amenity", "religion"):
        value = tags.get(key)
        if value:
            return str(value)
    return "point of interest"


def fetch_wikimedia_summary(city: str) -> str | None:
    try:
        response = httpx.get(
            WIKIMEDIA_SUMMARY_URL.format(title=city.replace(" ", "_")),
            headers={"User-Agent": USER_AGENT},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    extract = response.json().get("extract")
    return extract if isinstance(extract, str) and extract else None


def fetch_attractions(
    latitude: float,
    longitude: float,
    city: str | None = None,
    radius_m: int = 6000,
) -> list[AttractionSummary]:
    query = f"""
    [out:json][timeout:20];
    (
      node(around:{radius_m},{latitude},{longitude})["tourism"~"museum|attraction|viewpoint|gallery"];
      node(around:{radius_m},{latitude},{longitude})["historic"];
      node(around:{radius_m},{latitude},{longitude})["amenity"="place_of_worship"];
      way(around:{radius_m},{latitude},{longitude})["tourism"~"museum|attraction|viewpoint|gallery"];
      way(around:{radius_m},{latitude},{longitude})["historic"];
    );
    out center tags 20;
    """
    response = httpx.post(
        OVERPASS_URL,
        data={"data": query},
        headers={"User-Agent": USER_AGENT},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()

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
