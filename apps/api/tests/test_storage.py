from solo_api.models import Destination, Recommendation
from solo_api.storage import delete_travel_window, store_recommendation_result


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
