from solo_api.holidays import get_bank_holidays


def test_uk_2026_holidays_include_may_bank_holiday():
    holidays = get_bank_holidays(country="GB", year=2026)

    assert {"date": "2026-05-25", "name": "Spring bank holiday"} in holidays


def test_unknown_country_returns_empty_list():
    assert get_bank_holidays(country="ZZ", year=2026) == []
