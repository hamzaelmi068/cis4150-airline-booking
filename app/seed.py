"""Load static catalog from docs/seed.sql. Do not keep flight rows in Python."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from app.domain.enums import SeatStatus
from app.domain.models import Flight, Seat

DOCS = Path(__file__).resolve().parents[1] / "docs"
SCHEMA_PATH = DOCS / "postgres.sql"
SEED_PATH = DOCS / "seed.sql"

_FLIGHT_ROW = re.compile(
    r"INSERT INTO flights \([^)]+\) VALUES\s*\(\s*"
    r"'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)'\s*\)",
    re.IGNORECASE,
)
_SEAT_ROW = re.compile(
    r"INSERT INTO seats \([^)]+\) VALUES\s*\(\s*"
    r"'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*(\d+),\s*'([^']+)',\s*(NULL|'[^']*')\s*\)",
    re.IGNORECASE,
)


def sql_statements(path: Path) -> list[str]:
    """Split a SQL file into statements, ignoring `--` comments."""
    statements: list[str] = []
    buffer: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buffer.append(raw_line)
        if stripped.endswith(";"):
            statements.append("\n".join(buffer).strip())
            buffer = []
    return statements


def seed_catalog() -> tuple[list[Flight], list[Seat]]:
    """In-memory oracle reads the same SQL file Postgres executes."""
    sql = SEED_PATH.read_text(encoding="utf-8")
    flights = [
        Flight(
            id=match.group(1),
            flight_number=match.group(2),
            origin=match.group(3),
            destination=match.group(4),
            departure_time=_timestamp(match.group(5)),
        )
        for match in _FLIGHT_ROW.finditer(sql)
    ]
    seats = [
        Seat(
            id=match.group(1),
            flight_id=match.group(2),
            seat_number=match.group(3),
            cabin=match.group(4),
            price_cents=int(match.group(5)),
            status=SeatStatus(match.group(6)),
            booking_id=None if match.group(7) == "NULL" else match.group(7).strip("'"),
        )
        for match in _SEAT_ROW.finditer(sql)
    ]
    if not flights or not seats:
        raise ValueError(f"no catalog rows parsed from {SEED_PATH}")
    return flights, seats


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace(" ", "T"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
