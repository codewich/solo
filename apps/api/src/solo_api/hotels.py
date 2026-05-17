from datetime import date

from solo_api.models import HotelPriceSummary


def summarize_hotel_prices(
    city_code: str,
    check_in_date: date,
    check_out_date: date,
) -> HotelPriceSummary:
    return HotelPriceSummary(
        average_nightly_price=None,
        median_nightly_price=None,
        currency=None,
        sample_size=0,
        source="unavailable",
        status="unavailable",
    )
