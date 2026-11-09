from datetime import datetime, timedelta, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Return the current timezone-aware UTC time."""


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FakeClock:
    """Manual clock for expiry tests. `current` must be timezone-aware."""

    def __init__(self, current: datetime) -> None:
        if current.tzinfo is None:
            raise ValueError("FakeClock requires a timezone-aware datetime")
        self.current = current

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs: float) -> None:
        self.current = self.current + timedelta(**kwargs)
