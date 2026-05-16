from typing import Protocol

from solo_api.models import CostOfLivingSummary


class CostOfLivingProvider(Protocol):
    def summary_for(self, city: str, country: str) -> CostOfLivingSummary:
        ...


STATIC_COSTS: dict[tuple[str, str], CostOfLivingSummary] = {
    ("Lisbon", "Portugal"): CostOfLivingSummary(
        currency="EUR",
        meal_inexpensive=14.0,
        coffee=2.2,
        local_transport_ticket=2.0,
        summary=(
            "Lisbon is moderate for Western Europe, with food and transit usually friendly "
            "for solo weekends."
        ),
        source="Static Numbeo-compatible seed",
    ),
    ("Seville", "Spain"): CostOfLivingSummary(
        currency="EUR",
        meal_inexpensive=13.0,
        coffee=1.8,
        local_transport_ticket=1.4,
        summary=(
            "Seville is relatively affordable, especially for casual meals, coffee, "
            "and local transit."
        ),
        source="Static Numbeo-compatible seed",
    ),
    ("Porto", "Portugal"): CostOfLivingSummary(
        currency="EUR",
        meal_inexpensive=12.0,
        coffee=1.7,
        local_transport_ticket=1.8,
        summary=(
            "Porto keeps weekend costs manageable, with good value for meals and "
            "local movement."
        ),
        source="Static Numbeo-compatible seed",
    ),
}


class StaticCostOfLivingProvider:
    def summary_for(self, city: str, country: str) -> CostOfLivingSummary:
        seeded = STATIC_COSTS.get((city, country))
        if seeded is not None:
            return seeded

        return CostOfLivingSummary(
            currency="EUR",
            summary=(
                f"{city} has no static cost seed yet; show broad budget guidance until "
                "a live provider is configured."
            ),
            source="Static Numbeo-compatible seed",
        )
