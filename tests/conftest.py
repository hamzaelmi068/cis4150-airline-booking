from datetime import datetime, timezone

import pytest

from app.domain.clock import FakeClock
from app.repositories.memory import InMemoryBookingStore
from app.services.booking_service import BookingService
from app.services.payment import SimulatedPaymentGateway

START = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(START)


@pytest.fixture
def store() -> InMemoryBookingStore:
    return InMemoryBookingStore.with_seed_data()


@pytest.fixture
def service(store: InMemoryBookingStore, clock: FakeClock) -> BookingService:
    return BookingService(
        store=store,
        clock=clock,
        payment_gateway=SimulatedPaymentGateway(),
        hold_minutes=15,
    )
