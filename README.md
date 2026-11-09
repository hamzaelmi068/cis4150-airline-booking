# CIS*4150 Airline Ticket Booking

Small booking backend for the software testing project. It supports flight and seat lookup, seat holds, simulated payment, failed payment, cancellation, duplicate reservations, hold expiry, and concurrent booking attempts.

Business rules live in `app/services/booking_service.py`. HTTP routes do not decide transitions. All data lives in PostgreSQL. The mock flights and seats are in `docs/seed.sql`.

## Run

Everything needs PostgreSQL. Docker Compose starts it on host port 5433.

Whole app in Docker:

```powershell
docker compose up --build
```

Or only the database in Docker, with the API on your machine:

```powershell
docker compose up -d db
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:create_app --factory --reload
```

Interactive API docs: `http://127.0.0.1:8000/docs`

## Tests

```powershell
docker compose up -d db
.\.venv\Scripts\python -m pytest --cov=app --cov-report=term-missing
```

Tests use a separate `booking_test` database, which pytest creates on first run. Each test resets it to `docs/seed.sql`, so your app data in `booking` is never touched. If Postgres is not running, pytest stops at once with a message.

| Variable | Default | Used by |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://booking:booking@localhost:5433/booking` | the API |
| `TEST_DATABASE_URL` | `postgresql://booking:booking@localhost:5433/booking_test` | pytest |

## Mock data

`docs/seed.sql` holds the mock flights and seats. Schema: `docs/postgres.sql`. The app loads the seed on startup without overwriting existing rows. Tests depend on `flt-100` and `flt-200` keeping their ids, seats, and prices. Add or change other flights freely.

## Contract

See `docs/booking-model.md` for states, error codes, seed ids, and assumptions. See `docs/isp-test-design.md` for the input partitions and the tests that represent them. See `docs/postgres.sql` for the database handoff. See `docs/postgres-store.md` for the PostgreSQL store (Daman).

Decline a payment with token `fail`, `declined`, or `insufficient_funds`. Any other non-empty token succeeds.

## Team seams

- Ramy: cover `BookingService` and `is_active_reservation`. Inject a failing `PaymentGateway` through `create_app` for defect experiments.
- Daman: `PostgresBookingStore` implements `BookingStore` (`transaction()`, `lock_seat()`, `SELECT ... FOR UPDATE`). Pass it with `create_app(store=...)` or `DATABASE_URL`. Docker Compose and `.github/workflows/tests.yml` run the suite against PostgreSQL.
