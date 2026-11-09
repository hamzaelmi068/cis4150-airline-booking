from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import BookingStatus, SeatStatus


@dataclass(frozen=True)
class Flight:
    id: str
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime


@dataclass(frozen=True)
class Seat:
    id: str
    flight_id: str
    seat_number: str
    cabin: str
    price_cents: int
    status: SeatStatus
    booking_id: str | None = None


@dataclass(frozen=True)
class Booking:
    id: str
    flight_id: str
    seat_id: str
    passenger_name: str
    passenger_email: str
    status: BookingStatus
    price_cents: int
    created_at: datetime
    expires_at: datetime | None
    confirmed_at: datetime | None = None
    cancelled_at: datetime | None = None
    confirmation_code: str | None = None
    payment_reference: str | None = None
    failure_reason: str | None = None
