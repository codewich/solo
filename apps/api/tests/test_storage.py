from datetime import date

from solo_api.models import AirQualitySummary, Destination, Recommendation
from solo_api.storage import (
    delete_travel_window,
    get_air_quality_normal,
    list_travel_windows,
    store_air_quality_normal,
    store_recommendation_result,
)


def test_store_recommendation_result_writes_user_id_from_search(monkeypatch):
    captured = {}

    monkeypatch.setattr("solo_api.storage.database.is_database_configured", lambda: True)

    def fake_execute(sql, params):
        captured["sql"] = sql
        captured["params"] = params

    monkeypatch.setattr("solo_api.storage.database.execute", fake_execute)

    store_recommendation_result(
        search_id="7efc9d92-0a67-48b8-b1f4-7506932751ad",
        recommendation=Recommendation(
            travel_window_id="spring",
            destination=Destination(
                id="2267057",
                city="Lisbon",
                country="Portugal",
                latitude=38.7223,
                longitude=-9.1393,
            ),
            score=91,
            reasons=["Good fit."],
            caveats=[],
        ),
    )

    assert "insert into recommendation_results (search_id, user_id, city_id, score, payload)" in captured["sql"]
    assert "from recommendation_searches" in captured["sql"]
    assert "where id = %s" in captured["sql"]
    assert captured["params"][0] == "2267057"
    assert captured["params"][1] == 91
    assert captured["params"][3] == "7efc9d92-0a67-48b8-b1f4-7506932751ad"


def test_delete_travel_window_deletes_by_user_and_window(monkeypatch):
    calls = {}

    class FakeCursor:
        rowcount = 1

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def execute(self, sql, params):
            calls["sql"] = sql
            calls["params"] = params

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def cursor(self):
            return FakeCursor()

        def commit(self):
            calls["committed"] = True

    monkeypatch.setattr("solo_api.storage.database.is_database_configured", lambda: True)
    monkeypatch.setattr("solo_api.storage.database.connect", lambda: FakeConnection())

    assert delete_travel_window(user_id="user-1", travel_window_id="may") is True
    assert "delete from travel_windows" in calls["sql"]
    assert "where user_id = %s and id = %s" in calls["sql"]
    assert calls["params"] == ["user-1", "may"]
    assert calls["committed"] is True


def test_list_travel_windows_reads_user_windows_in_date_order(monkeypatch):
    captured = {}

    monkeypatch.setattr("solo_api.storage.database.is_database_configured", lambda: True)

    def fake_fetch_all(sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return [
            {
                "id": "range-saved",
                "label": "Saved Paris weekend",
                "start_date": date(2026, 5, 22),
                "end_date": date(2026, 5, 25),
                "status": "candidate",
            }
        ]

    monkeypatch.setattr("solo_api.storage.database.fetch_all", fake_fetch_all)

    windows = list_travel_windows(user_id="user-1")

    assert "from travel_windows" in captured["sql"]
    assert "where user_id = %s" in captured["sql"]
    assert "order by start_date asc, created_at asc" in captured["sql"]
    assert captured["params"] == ["user-1"]
    assert windows[0].id == "range-saved"
    assert windows[0].label == "Saved Paris weekend"


def test_get_air_quality_normal_reads_city_year_month(monkeypatch):
    captured = {}

    monkeypatch.setattr("solo_api.storage.database.is_database_configured", lambda: True)

    def fake_fetch_one(sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return {
            "european_aqi": 20.0,
            "us_aqi": 50.0,
            "pm25": 9.0,
            "pm10": 20.0,
            "no2": 25.0,
            "source": "Open-Meteo",
        }

    monkeypatch.setattr("solo_api.storage.database.fetch_one", fake_fetch_one)

    summary = get_air_quality_normal(city_id="2988507", year=2025, month=5)

    assert "from city_air_quality_normals" in captured["sql"]
    assert "where city_id = %s" in captured["sql"]
    assert "and year = %s" in captured["sql"]
    assert "and month = %s" in captured["sql"]
    assert captured["params"] == ["2988507", 2025, 5]
    assert summary is not None
    assert summary.european_aqi == 20.0
    assert summary.us_aqi == 50.0


def test_store_air_quality_normal_upserts_city_year_month(monkeypatch):
    captured = {}

    monkeypatch.setattr("solo_api.storage.database.is_database_configured", lambda: True)

    def fake_execute(sql, params):
        captured["sql"] = sql
        captured["params"] = params

    monkeypatch.setattr("solo_api.storage.database.execute", fake_execute)

    store_air_quality_normal(
        city_id="2988507",
        year=2025,
        month=5,
        air_quality=AirQualitySummary(
            european_aqi=20.0,
            us_aqi=50.0,
            pm25=9.0,
            pm10=20.0,
            no2=25.0,
            summary="Open-Meteo modeled air quality average.",
            source="Open-Meteo",
            status="available",
        ),
    )

    assert "insert into city_air_quality_normals" in captured["sql"]
    assert "on conflict (city_id, year, month) do update" in captured["sql"]
    assert captured["params"] == [
        "2988507",
        2025,
        5,
        20.0,
        50.0,
        9.0,
        20.0,
        25.0,
        "Open-Meteo",
    ]
