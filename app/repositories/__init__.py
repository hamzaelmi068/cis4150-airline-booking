"""Persistence adapters. The in-memory store is the reference behavior."""

from app.repositories.base import BookingStore
from app.repositories.memory import InMemoryBookingStore
from app.repositories.postgres import PostgresBookingStore

__all__ = ["BookingStore", "InMemoryBookingStore", "PostgresBookingStore"]
