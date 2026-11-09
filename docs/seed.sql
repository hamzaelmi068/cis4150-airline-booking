-- Static catalog. PostgresBookingStore loads this after docs/postgres.sql.
-- Tests depend on flt-100 and flt-200 keeping these ids, seats, and prices.
-- Other rows are mock flights for demos. There is no live airline feed.

INSERT INTO flights (id, flight_number, origin, destination, departure_time) VALUES
    ('flt-100', 'AC101', 'YYZ', 'YVR', '2026-12-01 15:00:00+00:00')
ON CONFLICT (id) DO NOTHING;

INSERT INTO flights (id, flight_number, origin, destination, departure_time) VALUES
    ('flt-200', 'AC202', 'YYZ', 'YUL', '2026-12-02 09:30:00+00:00')
ON CONFLICT (id) DO NOTHING;

INSERT INTO flights (id, flight_number, origin, destination, departure_time) VALUES
    ('flt-300', 'AC303', 'YYZ', 'YYC', '2026-12-03 18:45:00+00:00')
ON CONFLICT (id) DO NOTHING;

INSERT INTO flights (id, flight_number, origin, destination, departure_time) VALUES
    ('flt-400', 'WS412', 'YVR', 'YYZ', '2026-12-04 07:10:00+00:00')
ON CONFLICT (id) DO NOTHING;

INSERT INTO flights (id, flight_number, origin, destination, departure_time) VALUES
    ('flt-500', 'AC505', 'YUL', 'YVR', '2026-12-05 13:20:00+00:00')
ON CONFLICT (id) DO NOTHING;

INSERT INTO flights (id, flight_number, origin, destination, departure_time) VALUES
    ('flt-600', 'PD610', 'YYZ', 'YOW', '2026-12-06 11:00:00+00:00')
ON CONFLICT (id) DO NOTHING;

INSERT INTO flights (id, flight_number, origin, destination, departure_time) VALUES
    ('flt-700', 'AC717', 'YYC', 'YEG', '2026-12-07 16:30:00+00:00')
ON CONFLICT (id) DO NOTHING;

INSERT INTO flights (id, flight_number, origin, destination, departure_time) VALUES
    ('flt-800', 'TS820', 'YUL', 'FLL', '2026-12-08 22:15:00+00:00')
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-100-1A', 'flt-100', '1A', 'economy', 25000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-100-1B', 'flt-100', '1B', 'economy', 25000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-100-1C', 'flt-100', '1C', 'economy', 18000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-200-1A', 'flt-200', '1A', 'economy', 15000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-200-1B', 'flt-200', '1B', 'economy', 15000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-300-1A', 'flt-300', '1A', 'business', 89000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-300-1B', 'flt-300', '1B', 'business', 89000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-300-12A', 'flt-300', '12A', 'economy', 22000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-300-12B', 'flt-300', '12B', 'economy', 21000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-300-12C', 'flt-300', '12C', 'economy', 21000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-300-12D', 'flt-300', '12D', 'economy', 22000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-400-1A', 'flt-400', '1A', 'plus', 41000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-400-1B', 'flt-400', '1B', 'plus', 41000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-400-8A', 'flt-400', '8A', 'economy', 19500, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-400-8B', 'flt-400', '8B', 'economy', 18500, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-400-8C', 'flt-400', '8C', 'economy', 18500, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-500-1A', 'flt-500', '1A', 'business', 102000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-500-14A', 'flt-500', '14A', 'economy', 27500, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-500-14B', 'flt-500', '14B', 'economy', 26000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-500-14C', 'flt-500', '14C', 'economy', 26000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-500-14D', 'flt-500', '14D', 'economy', 27500, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-600-6A', 'flt-600', '6A', 'economy', 12900, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-600-6B', 'flt-600', '6B', 'economy', 11900, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-600-6C', 'flt-600', '6C', 'economy', 11900, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-600-6D', 'flt-600', '6D', 'economy', 12900, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-700-2A', 'flt-700', '2A', 'plus', 24000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-700-10A', 'flt-700', '10A', 'economy', 9900, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-700-10B', 'flt-700', '10B', 'economy', 8900, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-700-10C', 'flt-700', '10C', 'economy', 8900, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-800-1A', 'flt-800', '1A', 'business', 76000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-800-1B', 'flt-800', '1B', 'business', 76000, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-800-21A', 'flt-800', '21A', 'economy', 17900, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-800-21B', 'flt-800', '21B', 'economy', 16900, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-800-21C', 'flt-800', '21C', 'economy', 16900, 'available', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO seats (id, flight_id, seat_number, cabin, price_cents, status, booking_id) VALUES
    ('flt-800-21D', 'flt-800', '21D', 'economy', 17900, 'available', NULL)
ON CONFLICT (id) DO NOTHING;
