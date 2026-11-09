from collections.abc import Callable, Iterator
from datetime import datetime, timezone
import os

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
import pytest

from app.domain.clock import FakeClock
from app.domain.models import Flight, Seat
from app.repositories.base import BookingStore
from app.repositories.postgres import PostgresBookingStore
from app.services.booking_service import BookingService
from app.services.payment import SimulatedPaymentGateway

START = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
# A separate database, because every test truncates the tables.
DEFAULT_TEST_DATABASE_URL = "postgresql://booking:booking@localhost:5433/booking_test"
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


def _create_test_database(dsn: str) -> None:
    """Create the test database if missing. Stop the run if Postgres is down."""
    name = conninfo_to_dict(dsn)["dbname"]
    admin_dsn = make_conninfo(dsn, dbname="postgres", connect_timeout=5)
    try:
        with psycopg.connect(admin_dsn, autocommit=True) as conn:
            exists = conn.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (name,)
            ).fetchone()
            if not exists:
                conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    except psycopg.OperationalError as exc:
        pytest.exit(
            f"Cannot reach PostgreSQL for tests ({exc}).\n"
            "Start it with `docker compose up -d db`, or set TEST_DATABASE_URL.",
            returncode=1,
        )


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(START)


@pytest.fixture(scope="session")
def postgres_store() -> Iterator[PostgresBookingStore]:
    _create_test_database(TEST_DATABASE_URL)
    store = PostgresBookingStore.connect(TEST_DATABASE_URL)
    try:
        yield store
    finally:
        store.close()


@pytest.fixture
def store(postgres_store: PostgresBookingStore) -> PostgresBookingStore:
    postgres_store.reset_to_seed()
    return postgres_store


@pytest.fixture
def catalog_store(
    store: PostgresBookingStore,
) -> Callable[[list[Flight], list[Seat]], BookingStore]:
    def factory(flights: list[Flight], seats: list[Seat]) -> BookingStore:
        store.replace_catalog(flights, seats)
        return store

    return factory


@pytest.fixture
def service(store: BookingStore, clock: FakeClock) -> BookingService:
    return BookingService(
        store=store,
        clock=clock,
        payment_gateway=SimulatedPaymentGateway(),
        hold_minutes=15,
    )
