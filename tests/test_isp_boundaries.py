"""ISP values that the earlier tests did not represent.

The blocks themselves are described in docs/isp-test-design.md.
"""

import pytest

from app.domain.enums import BookingStatus, SeatStatus
from app.domain.errors import FlightNotFound, InvalidRequest
from app.domain.validation import MAX_NAME_LENGTH
from app.repositories.memory import InMemoryBookingStore
from app.services.booking_service import BookingService


def test_passenger_name_accepts_80_and_rejects_81(
    service: BookingService,
    store: InMemoryBookingStore,
) -> None:
    accepted = "A" * MAX_NAME_LENGTH
    held = service.hold_seat(
        "flt-100",
        "flt-100-1A",
        f"  {accepted}  ",
        "ada@example.com",
    )
    assert held.passenger_name == accepted
    assert len(held.passenger_name) == MAX_NAME_LENGTH

    with pytest.raises(InvalidRequest) as caught:
        service.hold_seat(
            "flt-100",
            "flt-100-1B",
            "B" * (MAX_NAME_LENGTH + 1),
            "grace@example.com",
        )
    assert "80" in caught.value.message
    assert store.get_seat("flt-100-1B").status == SeatStatus.AVAILABLE
    assert store.list_bookings_for_passenger("flt-100", "grace@example.com") == []


def test_hold_unknown_flight_does_not_reserve_a_seat(
    service: BookingService,
    store: InMemoryBookingStore,
) -> None:
    with pytest.raises(FlightNotFound):
        service.hold_seat("missing", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE
    assert store.list_bookings() == []


def test_blank_seat_id_is_rejected(service: BookingService, store: InMemoryBookingStore) -> None:
    with pytest.raises(InvalidRequest):
        service.hold_seat("flt-100", "   ", "Ada Lovelace", "ada@example.com")
    assert store.list_bookings() == []


def test_blank_payment_token_does_not_expire_elapsed_hold(
    service: BookingService,
    store: InMemoryBookingStore,
    clock,
) -> None:
    held = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    clock.advance(minutes=15)
    with pytest.raises(InvalidRequest):
        service.confirm_booking(held.id, "   ")
    assert store.get_booking(held.id).status == BookingStatus.HELD
    assert store.get_seat("flt-100-1A").status == SeatStatus.HELD


def test_invalid_passenger_name_does_not_expire_elapsed_hold(
    service: BookingService,
    store: InMemoryBookingStore,
    clock,
) -> None:
    held = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    clock.advance(minutes=15)
    with pytest.raises(InvalidRequest):
        service.hold_seat("flt-100", "flt-100-1B", "   ", "grace@example.com")
    assert store.get_booking(held.id).status == BookingStatus.HELD
    assert store.get_seat("flt-100-1A").status == SeatStatus.HELD
