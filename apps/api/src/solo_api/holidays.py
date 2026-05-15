HOLIDAYS: dict[tuple[str, int], list[dict[str, str]]] = {
    ("GB", 2026): [
        {"date": "2026-01-01", "name": "New Year's Day"},
        {"date": "2026-04-03", "name": "Good Friday"},
        {"date": "2026-04-06", "name": "Easter Monday"},
        {"date": "2026-05-04", "name": "Early May bank holiday"},
        {"date": "2026-05-25", "name": "Spring bank holiday"},
        {"date": "2026-08-31", "name": "Summer bank holiday"},
        {"date": "2026-12-25", "name": "Christmas Day"},
        {"date": "2026-12-28", "name": "Boxing Day substitute"},
    ]
}


def get_bank_holidays(country: str, year: int) -> list[dict[str, str]]:
    return HOLIDAYS.get((country.upper(), year), [])
