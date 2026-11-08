from app.domain.enums import BookingStatus


class BookingError(Exception):
    """Domain failure with a stable code for API clients and tests."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int,
        booking_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.booking_id = booking_id


class InvalidRequest(BookingError):
    def __init__(self, message: str) -> None:
        super().__init__("invalid_request", message, 400)


class FlightNotFound(BookingError):
    def __init__(self, flight_id: str) -> None:
        super().__init__(
            "flight_not_found",
            f"Flight '{flight_id}' was not found.",
            404,
        )


class SeatNotFound(BookingError):
    def __init__(self, seat_id: str, flight_id: str | None = None) -> None:
        if flight_id is None:
            message = f"Seat '{seat_id}' was not found."
        else:
            message = f"Seat '{seat_id}' is not on flight '{flight_id}'."
        super().__init__("seat_not_found", message, 404)


class BookingNotFound(BookingError):
    def __init__(self, booking_id: str) -> None:
        super().__init__(
            "booking_not_found",
            f"Booking '{booking_id}' was not found.",
            404,
        )


class SeatUnavailable(BookingError):
    def __init__(self, seat_id: str) -> None:
        super().__init__(
            "seat_unavailable",
            f"Seat '{seat_id}' is not available.",
            409,
        )


class DuplicateReservation(BookingError):
    def __init__(self, email: str, flight_id: str) -> None:
        super().__init__(
            "duplicate_reservation",
            f"Passenger '{email}' already has an active reservation on flight '{flight_id}'.",
            409,
        )


class HoldExpired(BookingError):
    def __init__(self, booking_id: str) -> None:
        super().__init__(
            "hold_expired",
            f"Hold for booking '{booking_id}' has expired.",
            409,
            booking_id=booking_id,
        )


class InvalidTransition(BookingError):
    def __init__(self, booking_id: str, status: BookingStatus, action: str) -> None:
        super().__init__(
            "invalid_transition",
            f"Cannot {action} booking '{booking_id}' while it is '{status.value}'.",
            409,
        )


class PaymentFailedError(BookingError):
    def __init__(self, booking_id: str, reason: str) -> None:
        super().__init__(
            "payment_failed",
            f"Payment was declined ({reason}).",
            402,
            booking_id=booking_id,
        )
        self.reason = reason
