"""Persistence adapters. PostgreSQL is the only store."""

from app.repositories.base import BookingStore
from app.repositories.postgres import PostgresBookingStore

__all__ = ["BookingStore", "PostgresBookingStore"]
