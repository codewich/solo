from datetime import date

import pytest

from solo_api.holidays import CalendarificProviderError, get_bank_holidays, get_holiday_regions
from solo_api.models import HolidayRegion, PublicHoliday


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_holidays_raise_without_calendarific_key(monkeypatch):
    monkeypatch.setattr("solo_api.holidays.get_env", lambda name: None)
    monkeypatch.setattr("solo_api.holidays.get_cached_public_holidays", lambda **kwargs: [])

    with pytest.raises(CalendarificProviderError, match="CALENDARIFIC_API_KEY"):
        get_bank_holidays(country="GB", year=2026)


def test_holidays_return_cached_rows_without_provider_call(monkeypatch):
    cached = [
        PublicHoliday(date=date(2026, 5, 25), name="Spring bank holiday", country_code="GB"),
    ]
    monkeypatch.setattr("solo_api.holidays.get_cached_public_holidays", lambda **kwargs: cached)

    def fail_get(*args, **kwargs):
        raise AssertionError("Calendarific should not be called on cache hit")

    monkeypatch.setattr("solo_api.holidays.httpx.get", fail_get)

    assert get_bank_holidays(country="GB", year=2026) == cached


def test_holidays_fetch_calendarific_and_store_public_holidays(monkeypatch):
    stored = {}
    monkeypatch.setattr("solo_api.holidays.get_env", lambda name: "key" if name == "CALENDARIFIC_API_KEY" else None)
    monkeypatch.setattr("solo_api.holidays.get_cached_public_holidays", lambda **kwargs: [])
    monkeypatch.setattr("solo_api.holidays.store_public_holidays", lambda **kwargs: stored.update(kwargs))

    def fake_get(url, params, headers, timeout):
        assert url == "https://calendarific.com/api/v2/holidays"
        assert params["country"] == "GB"
        assert params["year"] == 2026
        assert params["location"] == "gb-sct"
        return FakeResponse(
            {
                "meta": {"code": 200},
                "response": {
                    "holidays": [
                        {
                            "name": "Spring bank holiday",
                            "date": {"iso": "2026-05-25"},
                            "type": ["National holiday"],
                        },
                        {
                            "name": "Season starts",
                            "date": {"iso": "2026-06-01"},
                            "type": ["Observance"],
                        },
                    ]
                },
            }
        )

    monkeypatch.setattr("solo_api.holidays.httpx.get", fake_get)

    holidays = get_bank_holidays(country="GB", year=2026, region="gb-sct")

    assert [holiday.name for holiday in holidays] == ["Spring bank holiday"]
    assert stored["country_code"] == "GB"
    assert stored["year"] == 2026
    assert stored["region_code"] == "gb-sct"
    assert stored["holidays"] == holidays


def test_holiday_regions_use_cached_rows(monkeypatch):
    cached = [HolidayRegion(country_code="GB", region_code="gb-sct", name="Scotland")]
    monkeypatch.setattr("solo_api.holidays.get_cached_holiday_regions", lambda country_code: cached)

    assert get_holiday_regions("GB") == cached


def test_holiday_regions_return_empty_when_country_has_cached_empty_status(monkeypatch):
    monkeypatch.setattr("solo_api.holidays.get_cached_holiday_regions", lambda country_code: [])
    monkeypatch.setattr("solo_api.holidays.get_holiday_region_cache_status", lambda country_code: "empty")

    def fail_get(*args, **kwargs):
        raise AssertionError("Calendarific should not be called after empty region status is cached")

    monkeypatch.setattr("solo_api.holidays.httpx.get", fail_get)

    assert get_holiday_regions("PT") == []


def test_holiday_regions_do_not_call_provider_when_uk_regions_are_seeded(monkeypatch):
    cached = [
        HolidayRegion(country_code="GB", region_code="gb-eng", name="England"),
        HolidayRegion(country_code="GB", region_code="gb-wls", name="Wales"),
        HolidayRegion(country_code="GB", region_code="gb-sct", name="Scotland"),
        HolidayRegion(country_code="GB", region_code="gb-nir", name="Northern Ireland"),
    ]
    monkeypatch.setattr("solo_api.holidays.get_cached_holiday_regions", lambda country_code: cached)

    def fail_get(*args, **kwargs):
        raise AssertionError("Calendarific should not be called when seeded regions are in DB")

    monkeypatch.setattr("solo_api.holidays.httpx.get", fail_get)

    assert get_holiday_regions("GB") == cached


def test_holiday_regions_fall_back_to_known_uk_region_options(monkeypatch):
    monkeypatch.setattr("solo_api.holidays.get_cached_holiday_regions", lambda country_code: [])
    monkeypatch.setattr("solo_api.holidays.get_holiday_region_cache_status", lambda country_code: None)
    monkeypatch.setattr("solo_api.holidays.get_env", lambda name: None)
    monkeypatch.setattr("solo_api.holidays.store_holiday_regions", lambda *args, **kwargs: None)

    regions = get_holiday_regions("GB")

    assert {region.name for region in regions} >= {"England", "Scotland", "Northern Ireland"}
