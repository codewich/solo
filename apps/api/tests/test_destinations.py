from solo_api.destinations import load_destinations


def test_load_destinations_returns_seeded_cities():
    destinations = load_destinations()
    ids = {destination.id for destination in destinations}

    assert {"lisbon-pt", "porto-pt", "prague-cz", "copenhagen-dk", "seville-es"} <= ids


def test_destinations_include_recommendation_metadata():
    lisbon = next(destination for destination in load_destinations() if destination.id == "lisbon-pt")

    assert lisbon.short_stay_score >= 4
    assert "food" in lisbon.tags
    assert "spring" in lisbon.seasonal_strengths
