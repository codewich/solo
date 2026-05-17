from datetime import date

import pytest
from pydantic import ValidationError

from solo_api.models import TravelWindow


def test_travel_window_counts_inclusive_days():
    window = TravelWindow(id="may-bank", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25))

    assert window.duration_days == 3


def test_travel_window_keeps_minimal_planning_metadata():
    window = TravelWindow(
        id="warm-weekend",
        start_date=date(2026, 5, 22),
        end_date=date(2026, 5, 25),
        label="Warm long weekend",
        status="candidate",
    )

    assert window.label == "Warm long weekend"
    assert window.status == "candidate"


def test_travel_window_rejects_end_before_start():
    with pytest.raises(ValidationError):
        TravelWindow(id="bad", start_date=date(2026, 5, 25), end_date=date(2026, 5, 23))

