from solo_api.holidays import get_bank_holidays


def test_holidays_are_unavailable_without_provider():
    assert get_bank_holidays(country="GB", year=2026) == []

def test_unknown_country_returns_empty_list():
    assert get_bank_holidays(country="ZZ", year=2026) == []
