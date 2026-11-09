from dataclasses import replace

import pytest

from app.domain.enums import BookingStatus, SeatStatus
from app.domain.errors import (
    BookingNotFound,
    DuplicateReservation,
    FlightNotFound,
    HoldExpired,
    InvalidRequest,
    InvalidTransition,
    PaymentFailedError,
    SeatNotFound,
    SeatUnavailable,
)
from app.domain.models import Flight, Seat
from app.repositories.base import BookingStore
from app.services.booking_service import BookingService
from app.services.payment import PaymentResult, SimulatedPaymentGateway
from tests.conftest import START


def test_seed_catalog_is_stable(service: BookingService) -> None:
    flights = service.list_flights()
    ids = [flight.id for flight in flights]
    assert "flt-100" in ids
    assert "flt-200" in ids
    assert "flt-300" in ids
    seats = service.list_seats("flt-100")
    assert [seat.id for seat in seats] == ["flt-100-1A", "flt-100-1B", "flt-100-1C"]
    assert all(seat.status == SeatStatus.AVAILABLE for seat in seats)


def test_unknown_flight_and_seat(service: BookingService) -> None:
    with pytest.raises(FlightNotFound):
        service.get_flight("missing")
    with pytest.raises(FlightNotFound):
        service.list_seats("missing")
    with pytest.raises(SeatNotFound):
        service.hold_seat("flt-100", "missing", "Ada Lovelace", "ada@example.com")


def test_seat_on_another_flight_is_not_found(service: BookingService) -> None:
    with pytest.raises(SeatNotFound) as caught:
        service.hold_seat("flt-100", "flt-200-1A", "Ada Lovelace", "ada@example.com")
    assert "not on flight" in caught.value.message


def test_hold_confirm_and_block_second_reservation(service: BookingService, store: BookingStore) -> None:
    held = service.hold_seat("flt-100", "flt-100-1A", "  Ada   Lovelace ", "Ada@Example.com")
    assert held.status == BookingStatus.HELD
    assert held.passenger_name == "Ada Lovelace"
    assert held.passenger_email == "ada@example.com"
    assert held.expires_at == START.replace(minute=15)
    assert store.get_seat("flt-100-1A").status == SeatStatus.HELD

    confirmed = service.confirm_booking(held.id, "ok")
    assert confirmed.status == BookingStatus.CONFIRMED
    assert confirmed.confirmation_code is not None
    assert len(confirmed.confirmation_code) == 6
    assert confirmed.payment_reference == f"sim_{held.id[:8]}"
    assert store.get_seat("flt-100-1A").status == SeatStatus.BOOKED

    with pytest.raises(SeatUnavailable):
        service.hold_seat("flt-100", "flt-100-1A", "Grace Hopper", "grace@example.com")
    with pytest.raises(DuplicateReservation):
        service.hold_seat("flt-100", "flt-100-1B", "Ada Lovelace", "ada@example.com")

    other = service.hold_seat("flt-100", "flt-100-1B", "Grace Hopper", "grace@example.com")
    assert other.status == BookingStatus.HELD


def test_decline_tokens_release_the_seat(service: BookingService, store: BookingStore) -> None:
    held = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    with pytest.raises(PaymentFailedError) as caught:
        service.confirm_booking(held.id, "FAIL")
    assert caught.value.reason == "fail"
    assert caught.value.booking_id == held.id

    failed = store.get_booking(held.id)
    assert failed.status == BookingStatus.PAYMENT_FAILED
    assert failed.failure_reason == "fail"
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE

    with pytest.raises(InvalidTransition):
        service.confirm_booking(held.id, "ok")
    again = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    assert again.id != held.id


def test_non_positive_amount_is_a_payment_failure(clock, catalog_store) -> None:
    flight = Flight("flt-1", "T100", "YYZ", "YOW", START)
    seat = Seat("seat-1", "flt-1", "1A", "economy", 0, SeatStatus.AVAILABLE)
    store = catalog_store([flight], [seat])
    service = BookingService(store, clock, SimulatedPaymentGateway(), hold_minutes=15)
    held = service.hold_seat("flt-1", "seat-1", "Ada Lovelace", "ada@example.com")
    with pytest.raises(PaymentFailedError) as caught:
        service.confirm_booking(held.id, "ok")
    assert caught.value.reason == "invalid_amount"
    assert store.get_seat("seat-1").status == SeatStatus.AVAILABLE


def test_blank_payment_token_does_not_change_the_hold(service: BookingService, store: BookingStore) -> None:
    held = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    with pytest.raises(InvalidRequest):
        service.confirm_booking(held.id, "   ")
    assert store.get_booking(held.id).status == BookingStatus.HELD
    assert store.get_seat("flt-100-1A").status == SeatStatus.HELD


def test_expired_hold_is_not_charged(service: BookingService, store: BookingStore, clock) -> None:
    class RecordingGateway(SimulatedPaymentGateway):
        def __init__(self) -> None:
            self.calls = 0

        def charge(self, **kwargs) -> PaymentResult:
            self.calls += 1
            return super().charge(**kwargs)

    gateway = RecordingGateway()
    service._payment = gateway
    held = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    clock.advance(minutes=15)
    with pytest.raises(HoldExpired):
        service.confirm_booking(held.id, "fail")
    assert gateway.calls == 0
    assert store.get_booking(held.id).status == BookingStatus.EXPIRED
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE
    renewed = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    assert renewed.status == BookingStatus.HELD


def test_hold_still_confirms_one_second_before_expiry(service: BookingService, clock) -> None:
    held = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    clock.advance(minutes=15, seconds=-1)
    confirmed = service.confirm_booking(held.id, "tok_123")
    assert confirmed.status == BookingStatus.CONFIRMED


def test_missing_expiry_is_treated_as_expired(service: BookingService, store: BookingStore) -> None:
    held = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    store.save_booking(replace(store.get_booking(held.id), expires_at=None))
    with pytest.raises(HoldExpired):
        service.confirm_booking(held.id, "ok")
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE


def test_cancel_hold_and_confirmed_booking(service: BookingService, store: BookingStore) -> None:
    held = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    cancelled = service.cancel_booking(held.id)
    assert cancelled.status == BookingStatus.CANCELLED
    assert cancelled.cancelled_at is not None
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE
    with pytest.raises(InvalidTransition):
        service.cancel_booking(held.id)

    replacement = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    service.confirm_booking(replacement.id, "ok")
    service.cancel_booking(replacement.id)
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE
    follow_up = service.hold_seat("flt-100", "flt-100-1B", "Ada Lovelace", "ada@example.com")
    assert follow_up.status == BookingStatus.HELD


def test_cancel_expired_or_failed_booking_is_rejected(service: BookingService, clock) -> None:
    held = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    clock.advance(minutes=15)
    with pytest.raises(HoldExpired):
        service.cancel_booking(held.id)

    failed = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    with pytest.raises(PaymentFailedError):
        service.confirm_booking(failed.id, "declined")
    with pytest.raises(InvalidTransition):
        service.cancel_booking(failed.id)


def test_expiry_does_not_release_a_seat_owned_by_another_booking(
    service: BookingService,
    store: BookingStore,
    clock,
) -> None:
    held = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    store.save_seat(
        replace(store.get_seat("flt-100-1A"), status=SeatStatus.BOOKED, booking_id="other")
    )
    clock.advance(minutes=16)
    expired = service.expire_elapsed_holds()
    assert expired == 1
    assert service.expire_elapsed_holds() == 0
    seat = store.get_seat("flt-100-1A")
    assert seat.status == SeatStatus.BOOKED
    assert seat.booking_id == "other"
    assert store.get_booking(held.id).status == BookingStatus.EXPIRED


def test_get_booking_expires_lazily(service: BookingService, clock) -> None:
    held = service.hold_seat("flt-100", "flt-100-1C", "Ada Lovelace", "ada@example.com")
    clock.advance(minutes=15)
    seen = service.get_booking(held.id)
    assert seen.status == BookingStatus.EXPIRED
    available = service.list_seats("flt-100", SeatStatus.AVAILABLE)
    assert "flt-100-1C" in {seat.id for seat in available}


def test_confirm_rejects_a_seat_that_no_longer_matches_the_hold(
    service: BookingService,
    store: BookingStore,
) -> None:
    held = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    store.save_seat(replace(store.get_seat(held.seat_id), status=SeatStatus.BOOKED, booking_id="other"))
    with pytest.raises(InvalidTransition):
        service.confirm_booking(held.id, "ok")
    assert store.get_booking(held.id).status == BookingStatus.HELD


def test_passenger_validation(service: BookingService) -> None:
    with pytest.raises(InvalidRequest):
        service.hold_seat("flt-100", "flt-100-1A", "   ", "ada@example.com")
    with pytest.raises(InvalidRequest):
        service.hold_seat("flt-100", "flt-100-1A", "Ada", "not-an-email")
    with pytest.raises(InvalidRequest):
        service.hold_seat(" ", "flt-100-1A", "Ada", "ada@example.com")
    with pytest.raises(BookingNotFound):
        service.get_booking("missing")


def test_same_passenger_can_hold_a_seat_on_another_flight(service: BookingService) -> None:
    service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    other = service.hold_seat("flt-200", "flt-200-1A", "Ada Lovelace", "ada@example.com")
    assert other.flight_id == "flt-200"


def test_duplicate_passenger_wins_over_unavailable_seat(service: BookingService) -> None:
    service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    with pytest.raises(DuplicateReservation):
        service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ADA@example.com")


def test_store_returns_copies_and_releases_the_lock(store: BookingStore) -> None:
    original = store.get_seat("flt-100-1A")
    store.save_seat(replace(original, status=SeatStatus.BOOKED, booking_id="x"))
    assert original.status == SeatStatus.AVAILABLE
    assert store.get_seat("flt-100-1A").status == SeatStatus.BOOKED
    with pytest.raises(RuntimeError):
        store.lock_seat("flt-100-1A")
    with pytest.raises(RuntimeError):
        with store.transaction():
            raise RuntimeError("boom")
    assert store.get_flight("flt-100") is not None
