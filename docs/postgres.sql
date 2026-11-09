-- PostgreSQL shape for a BookingStore that matches the in-memory oracle.
-- Wire it in with create_app(store=your_store). Do not change BookingService
-- to talk to SQL directly.

CREATE TABLE IF NOT EXISTS flights (
    id TEXT PRIMARY KEY,
    flight_number TEXT NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_time TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS seats (
    id TEXT PRIMARY KEY,
    flight_id TEXT NOT NULL REFERENCES flights (id),
    seat_number TEXT NOT NULL,
    cabin TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('available', 'held', 'booked')),
    booking_id TEXT NULL,
    UNIQUE (flight_id, seat_number)
);

CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    flight_id TEXT NOT NULL REFERENCES flights (id),
    seat_id TEXT NOT NULL REFERENCES seats (id),
    passenger_name TEXT NOT NULL,
    passenger_email TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('held', 'confirmed', 'cancelled', 'expired', 'payment_failed')
    ),
    price_cents INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NULL,
    confirmed_at TIMESTAMPTZ NULL,
    cancelled_at TIMESTAMPTZ NULL,
    confirmation_code TEXT NULL,
    payment_reference TEXT NULL,
    failure_reason TEXT NULL
);

-- Service code expires old holds before inserting a new one, in the same
-- transaction. This index then rejects a second active row if two
-- transactions race on different seats for one passenger.
CREATE UNIQUE INDEX IF NOT EXISTS one_active_reservation_per_passenger
    ON bookings (flight_id, passenger_email)
    WHERE status IN ('held', 'confirmed');

-- lock_seat(seat_id) must run inside transaction() and should execute
-- SELECT id FROM seats WHERE id = :seat_id FOR UPDATE.
-- Translate a unique-index violation into DuplicateReservation.
-- The service calls lock_seat before reading the seat it is about to change.
-- get_* methods must return values the caller cannot use to mutate the row
-- without save_seat or save_booking.
