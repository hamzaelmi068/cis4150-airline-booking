# CIS*4150 Airline Ticket Booking

Small booking backend for the software testing project. It supports flight and seat lookup, seat holds, simulated payment, failed payment, cancellation, duplicate reservations, hold expiry, and concurrent booking attempts.

Business rules live in `app/services/booking_service.py`. HTTP routes do not decide transitions. The current store is in memory and is the reference behavior for a later PostgreSQL adapter.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload
.\.venv\Scripts\python -m pytest --cov=app --cov-report=term-missing
```

Interactive API docs: `http://127.0.0.1:8000/docs`

## PostgreSQL

`PostgresBookingStore` implements `BookingStore`. Set `DATABASE_URL` and `create_app()` uses it. Schema: `docs/postgres.sql`. Static flights and seats: `docs/seed.sql`.

```powershell
docker compose up --build
$env:DATABASE_URL = "postgresql://booking:booking@localhost:5432/booking"
.\.venv\Scripts\python -m pytest --cov=app --cov-report=term-missing
```

Without `DATABASE_URL`, the API and pytest keep using the in-memory store.

## Contract

See `docs/booking-model.md` for states, error codes, seed ids, and assumptions. See `docs/isp-test-design.md` for the input partitions and the tests that represent them. See `docs/postgres.sql` for the database handoff. See `docs/postgres-store.md` for the PostgreSQL store (Daman).

Decline a payment with token `fail`, `declined`, or `insufficient_funds`. Any other non-empty token succeeds.

## Team seams

- Ramy: cover `BookingService` and `is_active_reservation`. Inject a failing `PaymentGateway` through `create_app` for defect experiments.
- Daman: `PostgresBookingStore` implements `BookingStore` (`transaction()`, `lock_seat()`, `SELECT ... FOR UPDATE`). Pass it with `create_app(store=...)` or `DATABASE_URL`. Docker Compose and `.github/workflows/tests.yml` run the suite against PostgreSQL.
