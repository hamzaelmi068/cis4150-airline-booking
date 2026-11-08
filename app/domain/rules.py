from datetime import datetime

from app.domain.enums import BookingStatus


def is_active_reservation(
    status: BookingStatus,
    expires_at: datetime | None,
    now: datetime,
) -> bool:
    """A reservation blocks another hold for the same passenger on the flight.

    Confirmed bookings stay active until cancelled.
    A hold is active only while ``now < expires_at``.
    ``expires_at == now`` is already expired.
    A hold with no expiry is not active.
    """
    if status == BookingStatus.CONFIRMED:
        return True
    if status == BookingStatus.HELD:
        return expires_at is not None and expires_at > now
    return False
