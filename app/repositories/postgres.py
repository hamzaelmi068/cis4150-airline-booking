"""PostgreSQL BookingStore. Matches the in-memory oracle used by tests."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TypeVar

import psycopg
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.domain.enums import BookingStatus, SeatStatus
from app.domain.errors import BookingError, DuplicateReservation
from app.domain.models import Booking, Flight, Seat
from app.seed import SCHEMA_PATH, SEED_PATH, sql_statements

ACTIVE_RESERVATION_INDEX = "one_active_reservation_per_passenger"
T = TypeVar("T")


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _flight(row: dict) -> Flight:
    departure = _utc(row["departure_time"])
    assert departure is not None
    return Flight(
        id=row["id"],
        flight_number=row["flight_number"],
        origin=row["origin"],
        destination=row["destination"],
        departure_time=departure,
    )


def _seat(row: dict) -> Seat:
    return Seat(
        id=row["id"],
        flight_id=row["flight_id"],
        seat_number=row["seat_number"],
        cabin=row["cabin"],
        price_cents=row["price_cents"],
        status=SeatStatus(row["status"]),
        booking_id=row["booking_id"],
    )


def _booking(row: dict) -> Booking:
    created_at = _utc(row["created_at"])
    assert created_at is not None
    return Booking(
        id=row["id"],
        flight_id=row["flight_id"],
        seat_id=row["seat_id"],
        passenger_name=row["passenger_name"],
        passenger_email=row["passenger_email"],
        status=BookingStatus(row["status"]),
        price_cents=row["price_cents"],
        created_at=created_at,
        expires_at=_utc(row["expires_at"]),
        confirmed_at=_utc(row["confirmed_at"]),
        cancelled_at=_utc(row["cancelled_at"]),
        confirmation_code=row["confirmation_code"],
        payment_reference=row["payment_reference"],
        failure_reason=row["failure_reason"],
    )


@dataclass
class _TxState:
    conn: psycopg.Connection
    depth: int = 0
    aborted: bool = False


class PostgresBookingStore:
    """BookingStore backed by PostgreSQL.

    ``transaction()`` holds one connection for the whole service call.
    Domain errors such as ``PaymentFailedError`` commit, because the
    in-memory store keeps those writes. A unique-index violation aborts
    the transaction and becomes ``DuplicateReservation``.
    """

    def __init__(self, dsn: str, pool: ConnectionPool) -> None:
        self._dsn = dsn
        self._pool = pool
        self._local = threading.local()

    @classmethod
    def connect(cls, dsn: str, *, min_size: int = 1, max_size: int = 16) -> "PostgresBookingStore":
        pool = ConnectionPool(
            conninfo=dsn,
            min_size=min_size,
            max_size=max_size,
            timeout=30,
            open=True,
            kwargs={
                "row_factory": dict_row,
                "autocommit": False,
                "options": "-c timezone=UTC",
            },
        )
        pool.wait(timeout=30.0)
        store = cls(dsn, pool)
        store.ensure_ready()
        return store

    def close(self) -> None:
        self._pool.close()

    def ensure_ready(self) -> None:
        """Create tables if needed and insert the seed catalog without clobbering rows."""
        with self.transaction():
            self._apply_schema()
            self._apply_seed()

    def reset_to_seed(self) -> None:
        """Wipe bookings and restore the seed flights and seats. Used by tests."""
        with self.transaction():
            self._apply_schema()
            self._conn().execute("TRUNCATE bookings, seats, flights CASCADE")
            self._apply_seed()

    def replace_catalog(self, flights: list[Flight], seats: list[Seat]) -> None:
        """Replace the catalog. Used by tests that need a custom seat map."""
        with self.transaction():
            self._apply_schema()
            self._conn().execute("TRUNCATE bookings, seats, flights CASCADE")
            self._insert_flights(flights)
            self._insert_seats(seats, overwrite=True)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        state = getattr(self._local, "state", None)
        if state is None:
            state = _TxState(conn=self._pool.getconn())
            self._local.state = state
            owns = True
        else:
            owns = False
        state.depth += 1
        try:
            yield
            if owns:
                self._finish_tx(state, commit=not state.aborted)
        except BookingError:
            if owns:
                self._finish_tx(state, commit=not state.aborted)
            raise
        except Exception:
            if owns:
                self._finish_tx(state, commit=False)
            raise
        finally:
            state.depth -= 1
            if owns:
                self._pool.putconn(state.conn)
                self._local.state = None

    def lock_seat(self, seat_id: str) -> None:
        state = getattr(self._local, "state", None)
        if state is None or state.depth <= 0:
            raise RuntimeError("lock_seat must be called inside transaction()")
        if not isinstance(seat_id, str):
            raise RuntimeError("seat_id must be a string")
        state.conn.execute("SELECT id FROM seats WHERE id = %s FOR UPDATE", (seat_id,))

    def list_flights(self) -> list[Flight]:
        rows = self._fetch(
            "SELECT id, flight_number, origin, destination, departure_time "
            "FROM flights ORDER BY flight_number"
        )
        return [_flight(row) for row in rows]

    def get_flight(self, flight_id: str) -> Flight | None:
        row = self._fetchone(
            "SELECT id, flight_number, origin, destination, departure_time "
            "FROM flights WHERE id = %s",
            (flight_id,),
        )
        return _flight(row) if row else None

    def list_seats(self, flight_id: str) -> list[Seat]:
        rows = self._fetch(
            "SELECT id, flight_id, seat_number, cabin, price_cents, status, booking_id "
            "FROM seats WHERE flight_id = %s ORDER BY seat_number",
            (flight_id,),
        )
        return [_seat(row) for row in rows]

    def get_seat(self, seat_id: str) -> Seat | None:
        row = self._fetchone(
            "SELECT id, flight_id, seat_number, cabin, price_cents, status, booking_id "
            "FROM seats WHERE id = %s",
            (seat_id,),
        )
        return _seat(row) if row else None

    def save_seat(self, seat: Seat) -> None:
        self._execute(
            """
            INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                flight_id = EXCLUDED.flight_id,
                seat_number = EXCLUDED.seat_number,
                cabin = EXCLUDED.cabin,
                price_cents = EXCLUDED.price_cents,
                status = EXCLUDED.status,
                booking_id = EXCLUDED.booking_id
            """,
            (
                seat.id,
                seat.flight_id,
                seat.seat_number,
                seat.cabin,
                seat.price_cents,
                seat.status.value,
                seat.booking_id,
            ),
        )

    def get_booking(self, booking_id: str) -> Booking | None:
        row = self._fetchone(
            "SELECT id, flight_id, seat_id, passenger_name, passenger_email, status, "
            "price_cents, created_at, expires_at, confirmed_at, cancelled_at, "
            "confirmation_code, payment_reference, failure_reason "
            "FROM bookings WHERE id = %s",
            (booking_id,),
        )
        return _booking(row) if row else None

    def save_booking(self, booking: Booking) -> None:
        try:
            self._execute(
                """
                INSERT INTO bookings (
                    id, flight_id, seat_id, passenger_name, passenger_email, status,
                    price_cents, created_at, expires_at, confirmed_at, cancelled_at,
                    confirmation_code, payment_reference, failure_reason
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    flight_id = EXCLUDED.flight_id,
                    seat_id = EXCLUDED.seat_id,
                    passenger_name = EXCLUDED.passenger_name,
                    passenger_email = EXCLUDED.passenger_email,
                    status = EXCLUDED.status,
                    price_cents = EXCLUDED.price_cents,
                    created_at = EXCLUDED.created_at,
                    expires_at = EXCLUDED.expires_at,
                    confirmed_at = EXCLUDED.confirmed_at,
                    cancelled_at = EXCLUDED.cancelled_at,
                    confirmation_code = EXCLUDED.confirmation_code,
                    payment_reference = EXCLUDED.payment_reference,
                    failure_reason = EXCLUDED.failure_reason
                """,
                (
                    booking.id,
                    booking.flight_id,
                    booking.seat_id,
                    booking.passenger_name,
                    booking.passenger_email,
                    booking.status.value,
                    booking.price_cents,
                    booking.created_at,
                    booking.expires_at,
                    booking.confirmed_at,
                    booking.cancelled_at,
                    booking.confirmation_code,
                    booking.payment_reference,
                    booking.failure_reason,
                ),
            )
        except UniqueViolation as exc:
            state = getattr(self._local, "state", None)
            if state is not None:
                state.aborted = True
            constraint = exc.diag.constraint_name if exc.diag is not None else None
            if constraint == ACTIVE_RESERVATION_INDEX or ACTIVE_RESERVATION_INDEX in str(exc):
                raise DuplicateReservation(booking.passenger_email, booking.flight_id) from exc
            raise

    def list_bookings(self) -> list[Booking]:
        rows = self._fetch(
            "SELECT id, flight_id, seat_id, passenger_name, passenger_email, status, "
            "price_cents, created_at, expires_at, confirmed_at, cancelled_at, "
            "confirmation_code, payment_reference, failure_reason FROM bookings"
        )
        return [_booking(row) for row in rows]

    def list_bookings_for_passenger(self, flight_id: str, email: str) -> list[Booking]:
        rows = self._fetch(
            "SELECT id, flight_id, seat_id, passenger_name, passenger_email, status, "
            "price_cents, created_at, expires_at, confirmed_at, cancelled_at, "
            "confirmation_code, payment_reference, failure_reason "
            "FROM bookings WHERE flight_id = %s AND passenger_email = %s",
            (flight_id, email),
        )
        return [_booking(row) for row in rows]

    def _tx(self) -> _TxState | None:
        return getattr(self._local, "state", None)

    def _conn(self) -> psycopg.Connection:
        state = self._tx()
        if state is None:
            raise RuntimeError("database connection is only available inside transaction()")
        return state.conn

    def _finish_tx(self, state: _TxState, *, commit: bool) -> None:
        if commit:
            state.conn.commit()
        else:
            state.conn.rollback()
        state.aborted = False

    def _run(self, fn: Callable[[psycopg.Connection], T]) -> T:
        state = self._tx()
        if state is not None:
            return fn(state.conn)
        with self._pool.connection() as conn:
            return fn(conn)

    def _execute(self, sql: str, params: tuple | None = None) -> None:
        def op(conn: psycopg.Connection) -> None:
            conn.execute(sql, params)

        self._run(op)

    def _fetch(self, sql: str, params: tuple | None = None) -> list[dict]:
        def op(conn: psycopg.Connection) -> list[dict]:
            cursor = conn.execute(sql, params)
            return list(cursor.fetchall())

        return self._run(op)

    def _fetchone(self, sql: str, params: tuple | None = None) -> dict | None:
        def op(conn: psycopg.Connection) -> dict | None:
            return conn.execute(sql, params).fetchone()

        return self._run(op)

    def _apply_schema(self) -> None:
        self._run_sql_file(SCHEMA_PATH)

    def _apply_seed(self) -> None:
        self._run_sql_file(SEED_PATH)

    def _run_sql_file(self, path) -> None:
        conn = self._conn()
        for statement in sql_statements(path):
            conn.execute(statement)

    def _insert_flights(self, flights: list[Flight]) -> None:
        for flight in flights:
            self._execute(
                """
                INSERT INTO flights (id, flight_number, origin, destination, departure_time)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    flight_number = EXCLUDED.flight_number,
                    origin = EXCLUDED.origin,
                    destination = EXCLUDED.destination,
                    departure_time = EXCLUDED.departure_time
                """,
                (
                    flight.id,
                    flight.flight_number,
                    flight.origin,
                    flight.destination,
                    flight.departure_time,
                ),
            )

    def _insert_seats(self, seats: list[Seat], *, overwrite: bool) -> None:
        for seat in seats:
            if overwrite:
                self.save_seat(seat)
                continue
            self._execute(
                """
                INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    seat.id,
                    seat.flight_id,
                    seat.seat_number,
                    seat.cabin,
                    seat.price_cents,
                    seat.status.value,
                    seat.booking_id,
                ),
            )
