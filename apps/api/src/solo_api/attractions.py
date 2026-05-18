import httpx
import overpass

from solo_api.http import DEFAULT_TIMEOUT, USER_AGENT
from solo_api.models import AttractionSummary

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
WIKIMEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
WIKIMEDIA_GEOSEARCH_URL = "https://en.wikipedia.org/w/api.php"
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
ATTRACTION_TIMEOUT = httpx.Timeout(12.0, connect=4.0)
OVERPASS_TIMEOUT_SECONDS = 12
MIN_ATTRACTION_RESULTS = 3
MAX_ATTRACTION_RESULTS = 8


class AttractionLookupError(Exception):
    def __init__(self, *, service: str, message: str, original_error: Exception):
        self.service = service
        self.original_error = original_error
        super().__init__(message)


def _category(tags: dict) -> str:
    for key in ("historic", "tourism", "amenity", "leisure", "religion"):
        value = tags.get(key)
        if value:
            return str(value)
    return "point of interest"


def _name(tags: dict) -> str | None:
    for key in ("name:en", "int_name", "name"):
        value = tags.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


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


def fetch_wikimedia_nearby_attractions(
    *,
    latitude: float,
    longitude: float,
    city: str | None = None,
    radius_m: int = 10000,
    limit: int = 8,
) -> list[AttractionSummary]:
    try:
        response = httpx.get(
            WIKIMEDIA_GEOSEARCH_URL,
            params={
                "action": "query",
                "list": "geosearch",
                "gscoord": f"{latitude}|{longitude}",
                "gsradius": min(radius_m, 10000),
                "gslimit": limit,
                "format": "json",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    payload = response.json()
    pages = payload.get("query", {}).get("geosearch", []) if isinstance(payload, dict) else []
    if not isinstance(pages, list):
        return []

    city_name = city.casefold() if city else None
    results: list[AttractionSummary] = []
    for page in pages:
        title = page.get("title") if isinstance(page, dict) else None
        if not isinstance(title, str) or not title.strip():
            continue
        if city_name and title.casefold() == city_name:
            continue

        summary_payload = fetch_wikimedia_page_summary(title)
        description = summary_payload.get("extract")
        results.append(
            AttractionSummary(
                name=title,
                category="point of interest",
                latitude=page.get("lat"),
                longitude=page.get("lon"),
                description=description if isinstance(description, str) and description else None,
                source="Wikimedia",
            )
        )
        if len(results) == limit:
            break
    return results


def fetch_wikidata_nearby_attractions(
    *,
    latitude: float,
    longitude: float,
    city: str | None = None,
    radius_km: int = 25,
    limit: int = 8,
) -> list[AttractionSummary]:
    query = f"""
    SELECT ?item ?itemLabel ?location ?typeLabel WHERE {{
      SERVICE wikibase:around {{
        ?item wdt:P625 ?location.
        bd:serviceParam wikibase:center "Point({longitude} {latitude})"^^geo:wktLiteral;
          wikibase:radius "{radius_km}";
          wikibase:distance ?distance.
      }}
      OPTIONAL {{ ?item wdt:P31 ?type. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,zh". }}
    }}
    ORDER BY ?distance
    LIMIT {limit * 3}
    """
    try:
        response = httpx.get(
            WIKIDATA_SPARQL_URL,
            params={"query": query, "format": "json"},
            headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    payload = response.json()
    bindings = payload.get("results", {}).get("bindings", []) if isinstance(payload, dict) else []
    if not isinstance(bindings, list):
        return []

    city_name = city.casefold() if city else None
    results: list[AttractionSummary] = []
    seen_names: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        label = binding.get("itemLabel", {}).get("value")
        if not isinstance(label, str) or not label.strip():
            continue
        if city_name and label.casefold() == city_name:
            continue
        normalized_name = label.casefold()
        if normalized_name in seen_names:
            continue
        seen_names.add(normalized_name)
        latitude_value, longitude_value = _parse_wikidata_point(
            binding.get("location", {}).get("value")
        )
        type_label = binding.get("typeLabel", {}).get("value")
        results.append(
            AttractionSummary(
                name=label,
                category=type_label if isinstance(type_label, str) else "point of interest",
                latitude=latitude_value,
                longitude=longitude_value,
                description=None,
                source="Wikidata",
            )
        )
        if len(results) == limit:
            break
    return results


def _parse_wikidata_point(value: object) -> tuple[float | None, float | None]:
    if not isinstance(value, str) or not value.startswith("Point(") or not value.endswith(")"):
        return None, None
    parts = value.removeprefix("Point(").removesuffix(")").split()
    if len(parts) != 2:
        return None, None
    try:
        longitude, latitude = float(parts[0]), float(parts[1])
    except ValueError:
        return None, None
    return latitude, longitude


def _overpass_query(
    *,
    latitude: float,
    longitude: float,
    radius_m: int,
    include_historic: bool,
    broad: bool = False,
) -> str:
    historic_queries = (
        f"""
      node(around:{radius_m},{latitude},{longitude})["historic"~"castle|monument|archaeological_site"]["name"];
      way(around:{radius_m},{latitude},{longitude})["historic"~"castle|monument|archaeological_site|memorial|city_gate"]["name"];
      relation(around:{radius_m},{latitude},{longitude})["historic"~"castle|monument|archaeological_site|memorial|city_gate"]["name"];"""
        if include_historic
        else ""
    )
    broad_queries = (
        f"""
      node(around:{radius_m},{latitude},{longitude})["amenity"~"arts_centre|theatre|place_of_worship"]["name"];
      way(around:{radius_m},{latitude},{longitude})["amenity"~"arts_centre|theatre|place_of_worship"]["name"];
      relation(around:{radius_m},{latitude},{longitude})["amenity"~"arts_centre|theatre|place_of_worship"]["name"];
      node(around:{radius_m},{latitude},{longitude})["leisure"~"park|garden"]["name"];
      way(around:{radius_m},{latitude},{longitude})["leisure"~"park|garden"]["name"];
      relation(around:{radius_m},{latitude},{longitude})["leisure"~"park|garden"]["name"];"""
        if broad
        else ""
    )
    return f"""
    [out:json][timeout:12];
    (
      node(around:{radius_m},{latitude},{longitude})["tourism"~"museum|attraction|viewpoint|gallery|zoo|theme_park|aquarium"]["name"];
      way(around:{radius_m},{latitude},{longitude})["tourism"~"museum|attraction|viewpoint|gallery|zoo|theme_park|aquarium"]["name"];
      relation(around:{radius_m},{latitude},{longitude})["tourism"~"museum|attraction|viewpoint|gallery|zoo|theme_park|aquarium"]["name"];{historic_queries}{broad_queries}
    );
    out center tags qt {MAX_ATTRACTION_RESULTS * 2};
    """


def _post_overpass_query(query: str) -> httpx.Response:
    return httpx.post(
        OVERPASS_URL,
        data={"data": query},
        headers={"User-Agent": USER_AGENT},
        timeout=ATTRACTION_TIMEOUT,
    )


def _parse_overpass_attractions(
    payload: dict,
    *,
    destination_summary: str | None,
    seen_names: set[str],
    limit: int = MAX_ATTRACTION_RESULTS,
) -> list[AttractionSummary]:
    attractions: list[AttractionSummary] = []
    elements = payload.get("elements", [])
    if not isinstance(elements, list):
        return attractions

    for element in elements:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags", {})
        if not isinstance(tags, dict):
            continue
        name = _name(tags)
        if not name:
            continue
        normalized_name = name.casefold()
        if normalized_name in seen_names:
            continue
        seen_names.add(normalized_name)
        center = element.get("center", {})
        center = center if isinstance(center, dict) else {}
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
        if len(attractions) == limit:
            break

    return attractions


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
    response: httpx.Response | None = None
    overpass_error: AttractionLookupError | None = None
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
            overpass_error = AttractionLookupError(
                service="OpenStreetMap",
                message="OpenStreetMap timed out while querying nearby attractions.",
                original_error=retry_error,
            )
        except httpx.HTTPStatusError as retry_error:
            status_code = retry_error.response.status_code
            overpass_error = AttractionLookupError(
                service="OpenStreetMap",
                message=(
                    f"OpenStreetMap returned HTTP {status_code} "
                    "while querying nearby attractions."
                ),
                original_error=retry_error,
            )
        except httpx.HTTPError as retry_error:
            overpass_error = AttractionLookupError(
                service="OpenStreetMap",
                message="OpenStreetMap failed while querying nearby attractions.",
                original_error=retry_error,
            )
    except httpx.HTTPStatusError as error:
        status_code = error.response.status_code
        overpass_error = AttractionLookupError(
            service="OpenStreetMap",
            message=f"OpenStreetMap returned HTTP {status_code} while querying nearby attractions.",
            original_error=error,
        )
    except httpx.HTTPError as error:
        overpass_error = AttractionLookupError(
            service="OpenStreetMap",
            message="OpenStreetMap failed while querying nearby attractions.",
            original_error=error,
        )

    destination_summary = fetch_wikimedia_summary(city) if city and response is not None else None
    seen_names: set[str] = set()
    attractions = (
        _parse_overpass_attractions(
            response.json(),
            destination_summary=destination_summary,
            seen_names=seen_names,
        )
        if response is not None
        else []
    )
    if len(attractions) < MIN_ATTRACTION_RESULTS:
        try:
            broad_response = _post_overpass_query(
                _overpass_query(
                    latitude=latitude,
                    longitude=longitude,
                    radius_m=max(radius_m, 15000),
                    include_historic=True,
                    broad=True,
                )
            )
            broad_response.raise_for_status()
            attractions.extend(
                _parse_overpass_attractions(
                    broad_response.json(),
                    destination_summary=destination_summary,
                    seen_names=seen_names,
                    limit=MAX_ATTRACTION_RESULTS - len(attractions),
                )
            )
        except httpx.HTTPError:
            pass

    if len(attractions) < MIN_ATTRACTION_RESULTS:
        for attraction in fetch_wikimedia_nearby_attractions(
            latitude=latitude,
            longitude=longitude,
            city=city,
            radius_m=max(radius_m, 10000),
            limit=MAX_ATTRACTION_RESULTS,
        ):
            normalized_name = attraction.name.casefold()
            if normalized_name in seen_names:
                continue
            seen_names.add(normalized_name)
            attractions.append(attraction)
            if len(attractions) == MAX_ATTRACTION_RESULTS:
                break

    if len(attractions) < MIN_ATTRACTION_RESULTS:
        for attraction in fetch_wikidata_nearby_attractions(
            latitude=latitude,
            longitude=longitude,
            city=city,
            radius_km=25,
            limit=MAX_ATTRACTION_RESULTS,
        ):
            normalized_name = attraction.name.casefold()
            if normalized_name in seen_names:
                continue
            seen_names.add(normalized_name)
            attractions.append(attraction)
            if len(attractions) == MAX_ATTRACTION_RESULTS:
                break

    if not attractions and overpass_error is not None:
        raise overpass_error

    return attractions[:MAX_ATTRACTION_RESULTS]
