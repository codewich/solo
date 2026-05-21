import pytest

from solo_api.city_candidates import (
    CityCatalogNotReadyError,
    search_city_candidates,
    search_city_candidates_in_bounds,
)
from solo_api.models import Destination


def test_search_city_candidates_reads_imported_city_catalog(monkeypatch):
    expected = [
        Destination(
            id="2267057",
            city="Lisbon",
            country="PT",
            country_code="PT",
            region="14",
            timezone="Europe/Lisbon",
            latitude=38.7223,
            longitude=-9.1393,
            population=544851,
        )
    ]
    calls = []

    def fake_find_city_candidates(**kwargs):
        calls.append(kwargs)
        return expected

    monkeypatch.setattr("solo_api.city_candidates.has_imported_city_catalog", lambda: True)
    monkeypatch.setattr("solo_api.city_candidates.find_city_candidates", fake_find_city_candidates)

    cities = search_city_candidates(
        latitude=51.5072,
        longitude=-0.1276,
        radius_km=2000,
        min_population=250000,
        limit=12,
        region="PT",
        query="Lis",
    )

    assert cities == expected
    assert calls == [
        {
            "latitude": 51.5072,
            "longitude": -0.1276,
            "radius_km": 2000,
            "min_population": 250000,
            "limit": 12,
            "region": "PT",
            "query": "Lis",
        }
    ]


def test_search_city_candidates_returns_empty_for_valid_catalog_with_no_matches(monkeypatch):
    monkeypatch.setattr("solo_api.city_candidates.has_imported_city_catalog", lambda: True)
    monkeypatch.setattr("solo_api.city_candidates.find_city_candidates", lambda **kwargs: [])

    assert (
        search_city_candidates(
            latitude=51.5072,
            longitude=-0.1276,
            radius_km=10,
            min_population=10_000_000,
            limit=12,
        )
        == []
    )


def test_search_city_candidates_in_bounds_reads_imported_city_catalog(monkeypatch):
    expected = [
        Destination(
            id="2988507",
            city="Paris",
            country="FR",
            country_code="FR",
            region="11",
            timezone="Europe/Paris",
            latitude=48.8534,
            longitude=2.3488,
            population=2138551,
        )
    ]
    calls = []

    def fake_find_city_candidates_in_bounds(**kwargs):
        calls.append(kwargs)
        return expected

    monkeypatch.setattr("solo_api.city_candidates.has_imported_city_catalog", lambda: True)
    monkeypatch.setattr(
        "solo_api.city_candidates.find_city_candidates_in_bounds",
        fake_find_city_candidates_in_bounds,
    )

    cities = search_city_candidates_in_bounds(
        west=-1,
        south=48,
        east=3,
        north=52,
        min_population=250000,
        limit=10,
        region="FR",
        query="Par",
    )

    assert cities == expected
    assert calls == [
        {
            "west": -1,
            "south": 48,
            "east": 3,
            "north": 52,
            "min_population": 250000,
            "limit": 10,
            "region": "FR",
            "query": "Par",
        }
    ]


def test_search_city_candidates_in_bounds_returns_empty_for_valid_catalog_with_no_matches(
    monkeypatch,
):
    monkeypatch.setattr("solo_api.city_candidates.has_imported_city_catalog", lambda: True)
    monkeypatch.setattr("solo_api.city_candidates.find_city_candidates_in_bounds", lambda **kwargs: [])

    assert (
        search_city_candidates_in_bounds(
            west=-1,
            south=48,
            east=3,
            north=52,
            min_population=10_000_000,
            limit=12,
        )
        == []
    )


def test_search_city_candidates_requires_imported_city_catalog(monkeypatch):
    monkeypatch.setattr("solo_api.city_candidates.has_imported_city_catalog", lambda: False)

    with pytest.raises(CityCatalogNotReadyError, match="Import GeoNames cities15000"):
        search_city_candidates(
            latitude=51.5072,
            longitude=-0.1276,
            radius_km=2000,
            min_population=250000,
            limit=12,
        )


def test_search_city_candidates_in_bounds_requires_imported_city_catalog(monkeypatch):
    monkeypatch.setattr("solo_api.city_candidates.has_imported_city_catalog", lambda: False)

    with pytest.raises(CityCatalogNotReadyError, match="Import GeoNames cities15000"):
        search_city_candidates_in_bounds(
            west=-1,
            south=48,
            east=3,
            north=52,
            min_population=250000,
            limit=12,
        )
