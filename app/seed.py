"""Locate the SQL files PostgresBookingStore runs. Catalog rows live in docs/seed.sql."""

from __future__ import annotations

from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"
SCHEMA_PATH = DOCS / "postgres.sql"
SEED_PATH = DOCS / "seed.sql"


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
