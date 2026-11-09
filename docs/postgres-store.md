# Daman — PostgreSQL BookingStore

This is my part of the CIS*4150 booking backend: persistence. I did not write booking rules. Those stay in `BookingService`. I implemented the store that saves flights, seats, and bookings, then plugged it into the app.

## Assignment

- Implement `BookingStore` (`transaction()`, `lock_seat()`, and the read/write methods).
- Pass that store into `create_app(store=...)`.
- Use the schema in `docs/postgres.sql`.
- Keep static catalog data in SQL, not a Python list.

`app/repositories/base.py` is the **contract** (method names only). The real Postgres class is `PostgresBookingStore` in `app/repositories/postgres.py`. That is how this repo is set up: protocol in `base.py`, implementations beside it.

## How a request reaches my code

```
HTTP route (app/api/)
    -> BookingService (app/services/booking_service.py)
        -> self._store.<method>()
            -> PostgresBookingStore  (if DATABASE_URL is set)
            -> InMemoryBookingStore  (tests / no DATABASE_URL)
```

Example: `POST /bookings/holds` calls `service.hold_seat(...)`. The service then calls my store:

1. `transaction()` — one atomic unit of work
2. `get_flight()` — flight must exist
3. `lock_seat()` — nobody else can change that seat until we finish
4. `get_seat()` — read the locked row
5. `save_booking()` / `save_seat()` — write the hold

`BookingService` never runs SQL. It only calls the names in `base.py`. Python dispatches those calls to whichever store object was given to `create_app`.

## Where it is implemented

| File | What it is |
| --- | --- |
| `app/repositories/base.py` | `BookingStore` protocol. No SQL. |
| `app/repositories/postgres.py` | My implementation. All protocol methods + connection pool. |
| `app/repositories/memory.py` | In-memory oracle used by tests. Same method names. |
| `app/main.py` | `create_app(store=...)`. If `store` is omitted and `DATABASE_URL` is set, it builds `PostgresBookingStore`. |
| `docs/postgres.sql` | Tables, checks, unique index `one_active_reservation_per_passenger`. |
| `docs/seed.sql` | Static flights and seats (`INSERT`). Source of catalog data. |
| `app/seed.py` | Reads `docs/seed.sql` so the in-memory store stays in sync. No hardcoded flight list. |
| `Dockerfile`, `docker-compose.yml` | App + Postgres 16. |
| `.github/workflows/tests.yml` | One job on memory, one job on Postgres. |
| `tests/conftest.py` | If `DATABASE_URL` is set, pytest uses Postgres and resets seed each test. |
| `tests/test_postgres_store.py` | Store-specific checks (unique index → `DuplicateReservation`). |

## What each store method does (Postgres)

| Method in `base.py` | What `PostgresBookingStore` does |
| --- | --- |
| `transaction()` | Borrow one connection. Commit on success and on domain errors like `PaymentFailedError` (those writes must stay). Roll back on unexpected errors or a unique-index race. |
| `lock_seat(seat_id)` | Must be inside `transaction()`. Runs `SELECT id FROM seats WHERE id = %s FOR UPDATE`. |
| `list_flights()` / `get_flight()` | `SELECT` from `flights`. |
| `list_seats()` / `get_seat()` | `SELECT` from `seats`. Returns a new `Seat` object (copy-out). |
| `save_seat()` | `INSERT ... ON CONFLICT (id) DO UPDATE`. |
| `list_bookings()` / `get_booking()` / `list_bookings_for_passenger()` | `SELECT` from `bookings`. |
| `save_booking()` | `INSERT ... ON CONFLICT (id) DO UPDATE`. If the partial unique index fires, raise `DuplicateReservation`. |

On connect, `ensure_ready()` applies `docs/postgres.sql` then `docs/seed.sql`. Existing rows are not overwritten (`ON CONFLICT DO NOTHING`).

## Catalog

Flights and seats are **static SQL**, not live airline data.

- Tests need `flt-100` and `flt-200` to stay as they are (ids, seats, prices).
- Extra mock flights `flt-300` … `flt-800` are also in `docs/seed.sql`.

To change a route or price, edit `docs/seed.sql` only.

## How to run my part

```powershell
docker compose up --build
$env:DATABASE_URL = "postgresql://booking:booking@localhost:5432/booking"
.\.venv\Scripts\python -m pytest --cov=app --cov-report=term-missing
```

Without `DATABASE_URL`, the app and pytest keep using the in-memory store. That is expected.

Wire it by hand if needed:

```python
from app.main import create_app
from app.repositories.postgres import PostgresBookingStore

store = PostgresBookingStore.connect("postgresql://booking:booking@localhost:5432/booking")
app = create_app(store=store)
```

## What I did not change

- `BookingService` still owns hold / confirm / cancel / expiry rules.
- HTTP routes still do not talk to the database.
- In-memory store remains the behavior oracle. Postgres is supposed to match it, including concurrent holds (only one winner).
