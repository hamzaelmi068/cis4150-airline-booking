"""Graph coverage: booking lifecycle state graph.

Each test travels one edge (E1-E6) of the booking state graph
documented in docs/graph-coverage.md, and checks both the booking
status and the seat status after the transition.
"""

import pytest

from app.domain.enums import BookingStatus, SeatStatus
from app.domain.errors import PaymentFailedError, HoldExpired, InvalidTransition


def test_E1_hold_creates_held_booking(service, store):
    booking = service.hold_seat("flt-100", "flt-100-1A", "Ada", "ada@example.com")

    assert booking.status == BookingStatus.HELD
    assert store.get_seat("flt-100-1A").status == SeatStatus.HELD


def test_E2_payment_ok_confirms_booking(service, store):
    booking = service.hold_seat("flt-100", "flt-100-1A", "Ada", "ada@example.com")

    confirmed = service.confirm_booking(booking.id, "ok")

    assert confirmed.status == BookingStatus.CONFIRMED
    assert store.get_seat("flt-100-1A").status == SeatStatus.BOOKED


def test_E3_payment_declined_frees_seat(service, store):
    booking = service.hold_seat("flt-100", "flt-100-1A", "Ada", "ada@example.com")

    with pytest.raises(PaymentFailedError):
        service.confirm_booking(booking.id, "fail")

    assert store.get_booking(booking.id).status == BookingStatus.PAYMENT_FAILED
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE


def test_E4_cancel_held_booking_frees_seat(service, store):
    booking = service.hold_seat("flt-100", "flt-100-1A", "Ada", "ada@example.com")

    cancelled = service.cancel_booking(booking.id)

    assert cancelled.status == BookingStatus.CANCELLED
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE


def test_E5_cancel_confirmed_booking_frees_seat(service, store):
    booking = service.hold_seat("flt-100", "flt-100-1A", "Ada", "ada@example.com")
    confirmed = service.confirm_booking(booking.id, "ok")
    assert confirmed.status == BookingStatus.CONFIRMED

    cancelled = service.cancel_booking(booking.id)

    assert cancelled.status == BookingStatus.CANCELLED
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE


def test_E6_hold_expires_after_15_minutes(service, store, clock):
    booking = service.hold_seat("flt-100", "flt-100-1A", "Ada", "ada@example.com")

    clock.advance(minutes=15)
    expired = service.get_booking(booking.id)

    assert expired.status == BookingStatus.EXPIRED
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE



    

# Illegal transitions: confirm or cancel from a state that does not allow it.
# Each test reaches the state, tries the action, and checks nothing changed
 
 
def test_illegal_confirm_confirmed_booking(service, store):
    booking = service.hold_seat("flt-100", "flt-100-1A", "Ada", "ada@example.com")
    confirmed = service.confirm_booking(booking.id, "ok")
    assert confirmed.status == BookingStatus.CONFIRMED
 
    with pytest.raises(InvalidTransition):
        service.confirm_booking(booking.id, "ok")
 
    assert store.get_booking(booking.id).status == BookingStatus.CONFIRMED
    assert store.get_seat("flt-100-1A").status == SeatStatus.BOOKED
 
 
def test_illegal_confirm_cancelled_booking(service, store):
    booking = service.hold_seat("flt-100", "flt-100-1A", "Ada", "ada@example.com")
    service.cancel_booking(booking.id)
 
    with pytest.raises(InvalidTransition):
        service.confirm_booking(booking.id, "ok")
 
    assert store.get_booking(booking.id).status == BookingStatus.CANCELLED
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE
 
 
def test_illegal_cancel_cancelled_booking(service, store):
    booking = service.hold_seat("flt-100", "flt-100-1A", "Ada", "ada@example.com")
    cancelled = service.cancel_booking(booking.id)
    assert cancelled.status == BookingStatus.CANCELLED
 
    with pytest.raises(InvalidTransition):
        service.cancel_booking(booking.id)
 
    assert store.get_booking(booking.id).status == BookingStatus.CANCELLED
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE
 
 
def test_illegal_confirm_payment_failed_booking(service, store):
    booking = service.hold_seat("flt-100", "flt-100-1A", "Ada", "ada@example.com")
    with pytest.raises(PaymentFailedError):
        service.confirm_booking(booking.id, "fail")
 
    with pytest.raises(InvalidTransition):
        service.confirm_booking(booking.id, "ok")
 
    assert store.get_booking(booking.id).status == BookingStatus.PAYMENT_FAILED
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE
 
 
def test_illegal_cancel_payment_failed_booking(service, store):
    booking = service.hold_seat("flt-100", "flt-100-1A", "Ada", "ada@example.com")
    with pytest.raises(PaymentFailedError):
        service.confirm_booking(booking.id, "fail")
 
    with pytest.raises(InvalidTransition):
        service.cancel_booking(booking.id)
 
    assert store.get_booking(booking.id).status == BookingStatus.PAYMENT_FAILED
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE
 
 
def test_illegal_confirm_expired_booking(service, store, clock):
    booking = service.hold_seat("flt-100", "flt-100-1A", "Ada", "ada@example.com")
    clock.advance(minutes=15)
 
    with pytest.raises(HoldExpired):
        service.confirm_booking(booking.id, "ok")
 
    assert store.get_booking(booking.id).status == BookingStatus.EXPIRED
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE
 
 
def test_illegal_cancel_expired_booking(service, store, clock):
    booking = service.hold_seat("flt-100", "flt-100-1A", "Ada", "ada@example.com")
    clock.advance(minutes=15)
 
    with pytest.raises(HoldExpired):
        service.cancel_booking(booking.id)
 
    assert store.get_booking(booking.id).status == BookingStatus.EXPIRED
    assert store.get_seat("flt-100-1A").status == SeatStatus.AVAILABLE
 