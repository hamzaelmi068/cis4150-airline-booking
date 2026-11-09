import os

from fastapi import FastAPI

from app.api.errors import booking_error_handler
from app.api.router import api_router
from app.domain.clock import Clock, SystemClock
from app.domain.errors import BookingError
from app.repositories.base import BookingStore
from app.repositories.postgres import PostgresBookingStore
from app.services.booking_service import BookingService
from app.services.payment import PaymentGateway, SimulatedPaymentGateway

# Matches the db service in docker-compose.yml when the API runs on the host.
DEFAULT_DATABASE_URL = "postgresql://booking:booking@localhost:5433/booking"


def default_store() -> BookingStore:
    """Connect to PostgreSQL at DATABASE_URL, or the local Docker database."""
    return PostgresBookingStore.connect(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))


def create_app(
    store: BookingStore | None = None,
    clock: Clock | None = None,
    payment_gateway: PaymentGateway | None = None,
    hold_minutes: int = 15,
) -> FastAPI:
    """Build the API. Run with `uvicorn app.main:create_app --factory`.

    Tests inject a store pointed at the test database.
    """
    service = BookingService(
        store=store or default_store(),
        clock=clock or SystemClock(),
        payment_gateway=payment_gateway or SimulatedPaymentGateway(),
        hold_minutes=hold_minutes,
    )
    app = FastAPI(
        title="Airline Ticket Booking",
        version="0.1.0",
        summary="Course backend for holds, simulated payment, cancellation, and expiry.",
    )
    app.state.booking_service = service
    app.include_router(api_router)
    app.add_exception_handler(BookingError, booking_error_handler)
    return app
