"""Checks specific to PostgresBookingStore (Daman).

The rest of the suite also runs on Postgres through the `store` fixture in
conftest.py. These tests cover what only the database does: the SQL files,
the partial unique index, and row locking.
"""

import pytest

from app.domain.enums import BookingStatus
from app.domain.errors import DuplicateReservation
from app.domain.models import Booking
from app.seed import SCHEMA_PATH, SEED_PATH, sql_statements
from tests.conftest import START


def test_schema_file_is_executable_sql() -> None:
    # The splitter finds every table and the unique index in docs/postgres.sql.
    statements = sql_statements(SCHEMA_PATH)
    joined = "\n".join(statements)
    assert "CREATE TABLE IF NOT EXISTS flights" in joined
    assert "CREATE TABLE IF NOT EXISTS seats" in joined
    assert "CREATE TABLE IF NOT EXISTS bookings" in joined
    assert "one_active_reservation_per_passenger" in joined


def test_catalog_comes_from_seed_sql(store) -> None:
    # The mock data in docs/seed.sql is what ends up in the database.
    sql = SEED_PATH.read_text(encoding="utf-8")
    ids = {flight.id for flight in store.list_flights()}
    assert "INSERT INTO flights" in sql
    assert "INSERT INTO seats" in sql
    assert ids == {
        "flt-100",
        "flt-200",
        "flt-300",
        "flt-400",
        "flt-500",
        "flt-600",
        "flt-700",
        "flt-800",
    }
    assert store.get_seat("flt-100-1A").price_cents == 25000


def test_postgres_unique_index_becomes_duplicate_reservation(store) -> None:
    # Saves two active bookings for one passenger directly, skipping the
    # service checks, so only the database index can stop the second one.
    first = Booking(
        id="bk-1",
        flight_id="flt-100",
        seat_id="flt-100-1A",
        passenger_name="Ada Lovelace",
        passenger_email="ada@example.com",
        status=BookingStatus.HELD,
        price_cents=25000,
        created_at=START,
        expires_at=START.replace(minute=15),
    )
    second = Booking(
        id="bk-2",
        flight_id="flt-100",
        seat_id="flt-100-1B",
        passenger_name="Ada Lovelace",
        passenger_email="ada@example.com",
        status=BookingStatus.HELD,
        price_cents=25000,
        created_at=START,
        expires_at=START.replace(minute=15),
    )
    store.save_booking(first)
    with pytest.raises(DuplicateReservation):
        store.save_booking(second)
    # The first booking stays; the rejected one was never written.
    assert store.get_booking("bk-1") is not None
    assert store.get_booking("bk-2") is None


def test_postgres_lock_seat_requires_a_transaction(store) -> None:
    # A row lock outside a transaction would be released immediately, so it is an error.
    with pytest.raises(RuntimeError, match="inside transaction"):
        store.lock_seat("flt-100-1A")
    with store.transaction():
        store.lock_seat("flt-100-1A")
        store.lock_seat("missing-seat")  # locking a seat that doesn't exist is a no-op
