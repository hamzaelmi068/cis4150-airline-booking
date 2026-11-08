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

## Contract

See `docs/booking-model.md` for states, error codes, seed ids, and assumptions. See `docs/postgres.sql` for the database handoff.

Decline a payment with token `fail`, `declined`, or `insufficient_funds`. Any other non-empty token succeeds.

## Team seams

- Ramy: cover `BookingService` and `is_active_reservation`. Inject a failing `PaymentGateway` through `create_app` for defect experiments.
- Daman: implement `BookingStore`, including atomic `transaction()` and `lock_seat()`, then pass it to `create_app(store=...)`. Docker and the GitHub Actions workflow can replace `.github/workflows/tests.yml`.
