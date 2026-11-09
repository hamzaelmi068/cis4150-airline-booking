from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import BookingStatus, SeatStatus
from app.domain.validation import normalize_email, normalize_name


class FlightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime


class SeatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    flight_id: str
    seat_number: str
    cabin: str
    price_cents: int
    status: SeatStatus


class HoldRequest(BaseModel):
    flight_id: str
    seat_id: str
    passenger_name: str
    passenger_email: str

    @field_validator("flight_id", "seat_id")
    @classmethod
    def required_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("passenger_name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        return normalize_name(value)

    @field_validator("passenger_email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return normalize_email(value)


class ConfirmRequest(BaseModel):
    payment_token: str = Field(min_length=1)

    @field_validator("payment_token")
    @classmethod
    def required_token(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("payment_token is required")
        return cleaned


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ExpireHoldsResponse(BaseModel):
    expired: int
