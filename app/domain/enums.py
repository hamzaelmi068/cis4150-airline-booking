from enum import Enum


class SeatStatus(str, Enum):
    AVAILABLE = "available"
    HELD = "held"
    BOOKED = "booked"


class BookingStatus(str, Enum):
    HELD = "held"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAYMENT_FAILED = "payment_failed"
