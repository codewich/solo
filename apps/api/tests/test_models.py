from datetime import date

import pytest
from pydantic import ValidationError

from solo_api.models import PreferenceProfile, TravelWindow


def test_travel_window_counts_inclusive_days():
    window = TravelWindow(id="may-bank", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25))

    assert window.duration_days == 3


def test_travel_window_keeps_planning_metadata():
    window = TravelWindow(
        id="warm-weekend",
        start_date=date(2026, 5, 22),
        end_date=date(2026, 5, 25),
        label="Warm long weekend",
        linked_holiday="Spring bank holiday",
        status="candidate",
        notes="Prefer a relaxed food trip.",
    )

    assert window.label == "Warm long weekend"
    assert window.linked_holiday == "Spring bank holiday"
    assert window.status == "candidate"
    assert window.notes == "Prefer a relaxed food trip."


def test_travel_window_rejects_end_before_start():
    with pytest.raises(ValidationError):
        TravelWindow(id="bad", start_date=date(2026, 5, 25), end_date=date(2026, 5, 23))


def test_preference_profile_defaults_are_balanced():
    profile = PreferenceProfile()

    assert profile.pace == "balanced"
    assert profile.budget_sensitivity == 3
    assert "food" in profile.interests
