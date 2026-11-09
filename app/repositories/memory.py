import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace

from app.domain.models import Booking, Flight, Seat
from app.seed import seed_catalog


class InMemoryBookingStore:
    """Reference store. Copies go out; callers must save changes back.

    ``transaction()`` holds one re-entrant lock for the whole service call,
    so check-then-update is atomic inside this process. ``lock_seat`` checks
    that a transaction is open. It does not lock a single seat separately,
    because the process-wide lock already does.
    """

    def __init__(self, flights: list[Flight], seats: list[Seat]) -> None:
        if len({flight.id for flight in flights}) != len(flights):
            raise ValueError("duplicate flight id in catalog")
        if len({seat.id for seat in seats}) != len(seats):
            raise ValueError("duplicate seat id in catalog")
        self._lock = threading.RLock()
        self._tx_depth = 0
        self._flights = {flight.id: flight for flight in flights}
        self._seats = {seat.id: replace(seat) for seat in seats}
        self._bookings: dict[str, Booking] = {}

    @classmethod
    def with_seed_data(cls) -> "InMemoryBookingStore":
        flights, seats = seed_catalog()
        return cls(flights, seats)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self._lock:
            self._tx_depth += 1
            try:
                yield
            finally:
                self._tx_depth -= 1

    def lock_seat(self, seat_id: str) -> None:
        with self._lock:
            if self._tx_depth <= 0:
                raise RuntimeError("lock_seat must be called inside transaction()")
            if not isinstance(seat_id, str):
                raise RuntimeError("seat_id must be a string")

    def list_flights(self) -> list[Flight]:
        with self._lock:
            return sorted(self._flights.values(), key=lambda flight: flight.flight_number)

    def get_flight(self, flight_id: str) -> Flight | None:
        with self._lock:
            return self._flights.get(flight_id)

    def list_seats(self, flight_id: str) -> list[Seat]:
        with self._lock:
            seats = [replace(seat) for seat in self._seats.values() if seat.flight_id == flight_id]
            return sorted(seats, key=lambda seat: seat.seat_number)

    def get_seat(self, seat_id: str) -> Seat | None:
        with self._lock:
            seat = self._seats.get(seat_id)
            return replace(seat) if seat is not None else None

    def save_seat(self, seat: Seat) -> None:
        with self._lock:
            self._seats[seat.id] = replace(seat)

    def get_booking(self, booking_id: str) -> Booking | None:
        with self._lock:
            booking = self._bookings.get(booking_id)
            return replace(booking) if booking is not None else None

    def save_booking(self, booking: Booking) -> None:
        with self._lock:
            self._bookings[booking.id] = replace(booking)

    def list_bookings(self) -> list[Booking]:
        with self._lock:
            return [replace(booking) for booking in self._bookings.values()]

    def list_bookings_for_passenger(self, flight_id: str, email: str) -> list[Booking]:
        with self._lock:
            return [
                replace(booking)
                for booking in self._bookings.values()
                if booking.flight_id == flight_id and booking.passenger_email == email
            ]
