from datetime import datetime, timedelta, timezone

import pytest

from app.domain.enums import BookingStatus
from app.domain.rules import is_active_reservation

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)


def test_confirmed_reservation_stays_active_after_hold_window() -> None:
    assert is_active_reservation(BookingStatus.CONFIRMED, NOW - timedelta(hours=1), NOW)


def test_hold_is_active_before_expiry() -> None:
    assert is_active_reservation(BookingStatus.HELD, NOW + timedelta(seconds=1), NOW)


def test_hold_is_inactive_at_expiry_boundary() -> None:
    assert not is_active_reservation(BookingStatus.HELD, NOW, NOW)


def test_hold_without_expiry_is_inactive() -> None:
    assert not is_active_reservation(BookingStatus.HELD, None, NOW)


@pytest.mark.parametrize(
    "status",
    [
        BookingStatus.CANCELLED,
        BookingStatus.EXPIRED,
        BookingStatus.PAYMENT_FAILED,
    ],
)
def test_terminal_statuses_are_not_active(status: BookingStatus) -> None:
    assert not is_active_reservation(status, NOW + timedelta(hours=1), NOW)
