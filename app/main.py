import os

from fastapi import FastAPI

from app.api.errors import booking_error_handler
from app.api.router import api_router
from app.domain.clock import Clock, SystemClock
from app.domain.errors import BookingError
from app.repositories.base import BookingStore
from app.repositories.memory import InMemoryBookingStore
from app.repositories.postgres import PostgresBookingStore
from app.services.booking_service import BookingService
from app.services.payment import PaymentGateway, SimulatedPaymentGateway


def default_store() -> BookingStore:
    """Use PostgreSQL when DATABASE_URL is set; otherwise the in-memory oracle."""
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        return PostgresBookingStore.connect(dsn)
    return InMemoryBookingStore.with_seed_data()


def create_app(
    store: BookingStore | None = None,
    clock: Clock | None = None,
    payment_gateway: PaymentGateway | None = None,
    hold_minutes: int = 15,
) -> FastAPI:
    """Build the API. Tests and the Postgres store inject dependencies here."""
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


app = create_app()
