from datetime import datetime, timezone

from app.domain.enums import SeatStatus
from app.domain.models import Flight, Seat


def seed_catalog() -> tuple[list[Flight], list[Seat]]:
    """Small fixed catalog so tests and teammates share the same ids."""
    flights = [
        Flight(
            id="flt-100",
            flight_number="AC101",
            origin="YYZ",
            destination="YVR",
            departure_time=datetime(2026, 12, 1, 15, 0, tzinfo=timezone.utc),
        ),
        Flight(
            id="flt-200",
            flight_number="AC202",
            origin="YYZ",
            destination="YUL",
            departure_time=datetime(2026, 12, 2, 9, 30, tzinfo=timezone.utc),
        ),
    ]
    seat_plan = (
        ("flt-100", (("1A", 25000), ("1B", 25000), ("1C", 18000))),
        ("flt-200", (("1A", 15000), ("1B", 15000))),
    )
    seats: list[Seat] = []
    for flight_id, rows in seat_plan:
        for seat_number, price_cents in rows:
            seats.append(
                Seat(
                    id=f"{flight_id}-{seat_number}",
                    flight_id=flight_id,
                    seat_number=seat_number,
                    cabin="economy",
                    price_cents=price_cents,
                    status=SeatStatus.AVAILABLE,
                )
            )
    return flights, seats
