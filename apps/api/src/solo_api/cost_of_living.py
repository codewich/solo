from solo_api.models import CostOfLivingSummary


def unavailable_cost_of_living_summary(city: str) -> CostOfLivingSummary:
    return CostOfLivingSummary(
        currency="",
        meal_inexpensive=None,
        coffee=None,
        local_transport_ticket=None,
        summary=f"Cost of living data is unavailable for {city}.",
        source="unavailable",
        status="unavailable",
    )
