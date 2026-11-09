import pytest

from app.domain.enums import BookingStatus
from app.domain.errors import DuplicateReservation
from app.domain.models import Booking
from app.seed import SCHEMA_PATH, SEED_PATH, seed_catalog, sql_statements
from app.repositories.postgres import PostgresBookingStore
from tests.conftest import START


def test_schema_file_is_executable_sql() -> None:
    statements = sql_statements(SCHEMA_PATH)
    joined = "\n".join(statements)
    assert "CREATE TABLE IF NOT EXISTS flights" in joined
    assert "CREATE TABLE IF NOT EXISTS seats" in joined
    assert "CREATE TABLE IF NOT EXISTS bookings" in joined
    assert "one_active_reservation_per_passenger" in joined


def test_catalog_comes_from_seed_sql() -> None:
    sql = SEED_PATH.read_text(encoding="utf-8")
    flights, seats = seed_catalog()
    ids = {flight.id for flight in flights}
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
    assert any(seat.id == "flt-100-1A" and seat.price_cents == 25000 for seat in seats)


def test_postgres_unique_index_becomes_duplicate_reservation(store) -> None:
    if not isinstance(store, PostgresBookingStore):
        pytest.skip("PostgreSQL store only")

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
    assert store.get_booking("bk-1") is not None
    assert store.get_booking("bk-2") is None


def test_postgres_lock_seat_requires_a_transaction(store) -> None:
    if not isinstance(store, PostgresBookingStore):
        pytest.skip("PostgreSQL store only")
    with pytest.raises(RuntimeError, match="inside transaction"):
        store.lock_seat("flt-100-1A")
    with store.transaction():
        store.lock_seat("flt-100-1A")
        store.lock_seat("missing-seat")
