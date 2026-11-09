from contextlib import AbstractContextManager
from typing import Protocol

from app.domain.models import Booking, Flight, Seat


class BookingStore(Protocol):
    """Persistence contract used by BookingService.

    ``transaction()`` must make the whole service call atomic.
    ``lock_seat()`` must block other transactions from mutating that seat
    until the transaction ends. ``PostgresBookingStore`` does this with
    ``SELECT ... FOR UPDATE`` and the partial unique index in
    ``docs/postgres.sql``.
    """

    def transaction(self) -> AbstractContextManager[None]:
        """Run the enclosed reads and writes atomically."""

    def lock_seat(self, seat_id: str) -> None:
        """Exclusively lock one seat inside an open transaction."""

    def list_flights(self) -> list[Flight]:
        """Return every flight, in a stable order."""

    def get_flight(self, flight_id: str) -> Flight | None:
        """Return one flight, or None."""

    def list_seats(self, flight_id: str) -> list[Seat]:
        """Return seats for one flight, in a stable order."""

    def get_seat(self, seat_id: str) -> Seat | None:
        """Return a copy of one seat, or None."""

    def save_seat(self, seat: Seat) -> None:
        """Insert or replace a seat."""

    def get_booking(self, booking_id: str) -> Booking | None:
        """Return a copy of one booking, or None."""

    def save_booking(self, booking: Booking) -> None:
        """Insert or replace a booking."""

    def list_bookings(self) -> list[Booking]:
        """Return a copy of every booking."""

    def list_bookings_for_passenger(self, flight_id: str, email: str) -> list[Booking]:
        """Return bookings for one passenger email on one flight."""
