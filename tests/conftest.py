from collections.abc import Callable, Iterator
from datetime import datetime, timezone
import os

import pytest

from app.domain.clock import FakeClock
from app.domain.models import Flight, Seat
from app.repositories.base import BookingStore
from app.repositories.memory import InMemoryBookingStore
from app.repositories.postgres import PostgresBookingStore
from app.services.booking_service import BookingService
from app.services.payment import SimulatedPaymentGateway

START = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
DATABASE_URL = os.environ.get("DATABASE_URL")


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(START)


@pytest.fixture(scope="session")
def postgres_store() -> Iterator[PostgresBookingStore | None]:
    if not DATABASE_URL:
        yield None
        return
    store = PostgresBookingStore.connect(DATABASE_URL)
    try:
        yield store
    finally:
        store.close()


@pytest.fixture
def store(postgres_store: PostgresBookingStore | None) -> Iterator[BookingStore]:
    if postgres_store is None:
        yield InMemoryBookingStore.with_seed_data()
        return
    postgres_store.reset_to_seed()
    yield postgres_store


@pytest.fixture
def catalog_store(
    store: BookingStore,
) -> Callable[[list[Flight], list[Seat]], BookingStore]:
    def factory(flights: list[Flight], seats: list[Seat]) -> BookingStore:
        if isinstance(store, PostgresBookingStore):
            store.replace_catalog(flights, seats)
            return store
        return InMemoryBookingStore(flights, seats)

    return factory


@pytest.fixture
def service(store: BookingStore, clock: FakeClock) -> BookingService:
    return BookingService(
        store=store,
        clock=clock,
        payment_gateway=SimulatedPaymentGateway(),
        hold_minutes=15,
    )
