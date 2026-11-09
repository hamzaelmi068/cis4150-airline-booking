import secrets
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta
from uuid import uuid4

from app.domain.clock import Clock
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
from app.domain.models import Booking, Flight, Seat
from app.domain.rules import is_active_reservation
from app.domain.validation import normalize_email, normalize_name
from app.repositories.base import BookingStore
from app.services.payment import PaymentGateway


class BookingService:
    """Booking transitions. Routes should call this and not touch the store.

    Successful calls expire elapsed holds before the requested change.
    Invalid passenger input and a blank payment token do not.

    Check order for a new hold:
    flight exists, seat exists on that flight, passenger has no active
    reservation, then the seat is available. When the passenger already
    has an active reservation, the error is duplicate_reservation even if
    the requested seat is also taken.
    """

    def __init__(
        self,
        store: BookingStore,
        clock: Clock,
        payment_gateway: PaymentGateway,
        hold_minutes: int = 15,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        if hold_minutes <= 0:
            raise ValueError("hold_minutes must be positive")
        self._store = store
        self._clock = clock
        self._payment = payment_gateway
        self._hold_duration = timedelta(minutes=hold_minutes)
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def list_flights(self) -> list[Flight]:
        return self._store.list_flights()

    def get_flight(self, flight_id: str) -> Flight:
        flight = self._store.get_flight(flight_id)
        if flight is None:
            raise FlightNotFound(flight_id)
        return flight

    def list_seats(self, flight_id: str, status: SeatStatus | None = None) -> list[Seat]:
        now = self._clock.now()
        with self._store.transaction():
            self._expire_elapsed(now)
            if self._store.get_flight(flight_id) is None:
                raise FlightNotFound(flight_id)
            seats = self._store.list_seats(flight_id)
        if status is not None:
            return [seat for seat in seats if seat.status == status]
        return seats

    def hold_seat(
        self,
        flight_id: str,
        seat_id: str,
        passenger_name: str,
        passenger_email: str,
    ) -> Booking:
        name, email = self._passenger(passenger_name, passenger_email)
        flight_id = flight_id.strip()
        seat_id = seat_id.strip()
        if not flight_id or not seat_id:
            raise InvalidRequest("flight_id and seat_id are required")

        now = self._clock.now()
        with self._store.transaction():
            self._expire_elapsed(now)
            if self._store.get_flight(flight_id) is None:
                raise FlightNotFound(flight_id)
            self._store.lock_seat(seat_id)
            seat = self._store.get_seat(seat_id)
            if seat is None:
                raise SeatNotFound(seat_id)
            if seat.flight_id != flight_id:
                raise SeatNotFound(seat_id, flight_id)
            if self._passenger_has_active_reservation(flight_id, email, now):
                raise DuplicateReservation(email, flight_id)
            if seat.status != SeatStatus.AVAILABLE or seat.booking_id is not None:
                raise SeatUnavailable(seat_id)

            booking = Booking(
                id=self._id_factory(),
                flight_id=flight_id,
                seat_id=seat.id,
                passenger_name=name,
                passenger_email=email,
                status=BookingStatus.HELD,
                price_cents=seat.price_cents,
                created_at=now,
                expires_at=now + self._hold_duration,
            )
            self._store.save_booking(booking)
            self._store.save_seat(
                replace(seat, status=SeatStatus.HELD, booking_id=booking.id)
            )
            return booking

    def confirm_booking(self, booking_id: str, payment_token: str) -> Booking:
        token = payment_token.strip()
        if not token:
            raise InvalidRequest("payment_token is required")

        now = self._clock.now()
        with self._store.transaction():
            self._expire_elapsed(now)
            booking = self._require_booking(booking_id)
            if booking.status == BookingStatus.EXPIRED:
                raise HoldExpired(booking.id)
            if booking.status != BookingStatus.HELD:
                raise InvalidTransition(booking.id, booking.status, "confirm")

            self._store.lock_seat(booking.seat_id)
            seat = self._store.get_seat(booking.seat_id)
            if (
                seat is None
                or seat.booking_id != booking.id
                or seat.status != SeatStatus.HELD
            ):
                raise InvalidTransition(booking.id, booking.status, "confirm")

            result = self._payment.charge(
                amount_cents=booking.price_cents,
                payment_token=token,
                booking_id=booking.id,
            )
            if not result.success:
                # Save payment_failed and release the seat, then raise.
                # The exception does not roll the failure back.
                reason = result.reason or "declined"
                failed = replace(
                    booking,
                    status=BookingStatus.PAYMENT_FAILED,
                    failure_reason=reason,
                )
                self._store.save_booking(failed)
                self._release_seat(failed)
                raise PaymentFailedError(failed.id, reason)

            confirmed = replace(
                booking,
                status=BookingStatus.CONFIRMED,
                confirmed_at=now,
                confirmation_code=secrets.token_hex(3).upper(),
                payment_reference=result.reference,
                failure_reason=None,
            )
            self._store.save_booking(confirmed)
            self._store.save_seat(
                replace(seat, status=SeatStatus.BOOKED, booking_id=confirmed.id)
            )
            return confirmed

    def cancel_booking(self, booking_id: str) -> Booking:
        now = self._clock.now()
        with self._store.transaction():
            self._expire_elapsed(now)
            booking = self._require_booking(booking_id)
            if booking.status == BookingStatus.EXPIRED:
                raise HoldExpired(booking.id)
            if booking.status not in (BookingStatus.HELD, BookingStatus.CONFIRMED):
                raise InvalidTransition(booking.id, booking.status, "cancel")
            cancelled = replace(
                booking,
                status=BookingStatus.CANCELLED,
                cancelled_at=now,
            )
            self._store.save_booking(cancelled)
            self._release_seat(cancelled)
            return cancelled

    def get_booking(self, booking_id: str) -> Booking:
        now = self._clock.now()
        with self._store.transaction():
            self._expire_elapsed(now)
            return self._require_booking(booking_id)

    def expire_elapsed_holds(self) -> int:
        now = self._clock.now()
        with self._store.transaction():
            return self._expire_elapsed(now)

    def _passenger(self, passenger_name: str, passenger_email: str) -> tuple[str, str]:
        try:
            return normalize_name(passenger_name), normalize_email(passenger_email)
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc

    def _require_booking(self, booking_id: str) -> Booking:
        booking = self._store.get_booking(booking_id)
        if booking is None:
            raise BookingNotFound(booking_id)
        return booking

    def _passenger_has_active_reservation(
        self,
        flight_id: str,
        email: str,
        now: datetime,
    ) -> bool:
        for existing in self._store.list_bookings_for_passenger(flight_id, email):
            if is_active_reservation(existing.status, existing.expires_at, now):
                return True
        return False

    def _expire_elapsed(self, now: datetime) -> int:
        expired = 0
        for booking in self._store.list_bookings():
            if booking.status != BookingStatus.HELD:
                continue
            if is_active_reservation(booking.status, booking.expires_at, now):
                continue
            self._store.save_booking(replace(booking, status=BookingStatus.EXPIRED))
            self._release_seat(booking)
            expired += 1
        return expired

    def _release_seat(self, booking: Booking) -> None:
        self._store.lock_seat(booking.seat_id)
        seat = self._store.get_seat(booking.seat_id)
        # Skip the seat when another booking already owns it.
        if seat is None or seat.booking_id != booking.id:
            return
        self._store.save_seat(
            replace(seat, status=SeatStatus.AVAILABLE, booking_id=None)
        )
