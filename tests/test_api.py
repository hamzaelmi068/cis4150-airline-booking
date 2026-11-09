from datetime import timedelta

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.base import BookingStore


def test_health_flights_and_seat_filter(clock, store: BookingStore) -> None:
    with TestClient(create_app(store=store, clock=clock)) as client:
        assert client.get("/health").json() == {"status": "ok"}
        flights = client.get("/flights")
        assert flights.status_code == 200
        flight_ids = [flight["id"] for flight in flights.json()]
        assert "flt-100" in flight_ids
        assert "flt-200" in flight_ids
        assert "flt-800" in flight_ids
        missing = client.get("/flights/nope")
        assert missing.status_code == 404
        assert missing.json()["error"] == "flight_not_found"
        seats = client.get("/flights/flt-100/seats", params={"status": "available"})
        assert len(seats.json()) == 3
        invalid = client.get("/flights/flt-100/seats", params={"status": "nope"})
        assert invalid.status_code == 422


def test_http_booking_flow(clock, store: BookingStore) -> None:
    with TestClient(create_app(store=store, clock=clock, hold_minutes=15)) as client:
        rejected = client.post(
            "/bookings/holds",
            json={
                "flight_id": "flt-100",
                "seat_id": "flt-100-1A",
                "passenger_name": "Ada",
                "passenger_email": "not-an-email",
            },
        )
        assert rejected.status_code == 422

        held = client.post(
            "/bookings/holds",
            json={
                "flight_id": "flt-100",
                "seat_id": "flt-100-1A",
                "passenger_name": "Ada Lovelace",
                "passenger_email": "Ada@Example.com",
            },
        )
        assert held.status_code == 201
        body = held.json()
        assert body["status"] == "held"
        assert body["passenger_email"] == "ada@example.com"
        assert body["price_cents"] == 25000

        conflict = client.post(
            "/bookings/holds",
            json={
                "flight_id": "flt-100",
                "seat_id": "flt-100-1A",
                "passenger_name": "Grace Hopper",
                "passenger_email": "grace@example.com",
            },
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"] == "seat_unavailable"

        declined = client.post(f"/bookings/{body['id']}/confirm", json={"payment_token": "insufficient_funds"})
        assert declined.status_code == 402
        assert declined.json()["error"] == "payment_failed"
        assert declined.json()["booking_id"] == body["id"]

        held_again = client.post(
            "/bookings/holds",
            json={
                "flight_id": "flt-100",
                "seat_id": "flt-100-1A",
                "passenger_name": "Ada Lovelace",
                "passenger_email": "ada@example.com",
            },
        )
        booking_id = held_again.json()["id"]
        confirmed = client.post(f"/bookings/{booking_id}/confirm", json={"payment_token": "ok"})
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "confirmed"
        assert confirmed.json()["confirmation_code"]

        second = client.post(f"/bookings/{booking_id}/confirm", json={"payment_token": "ok"})
        assert second.status_code == 409
        assert second.json()["error"] == "invalid_transition"

        cancelled = client.post(f"/bookings/{booking_id}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
        seats = client.get("/flights/flt-100/seats").json()
        seat = next(item for item in seats if item["id"] == "flt-100-1A")
        assert seat["status"] == "available"


def test_get_booking_reports_expiry(clock, store: BookingStore) -> None:
    app = create_app(store=store, clock=clock, hold_minutes=15)
    with TestClient(app) as client:
        created = client.post(
            "/bookings/holds",
            json={
                "flight_id": "flt-200",
                "seat_id": "flt-200-1B",
                "passenger_name": "Grace Hopper",
                "passenger_email": "grace@example.com",
            },
        )
        booking_id = created.json()["id"]
        clock.advance(minutes=15)
        seen = client.get(f"/bookings/{booking_id}")
        assert seen.status_code == 200
        assert seen.json()["status"] == "expired"
        swept = client.post("/maintenance/expire-holds")
        assert swept.json() == {"expired": 0}
        seats = client.get("/flights/flt-200/seats").json()
        seat = next(item for item in seats if item["id"] == "flt-200-1B")
        assert seat["status"] == "available"


def test_duplicate_reservation_http_code(clock, store: BookingStore) -> None:
    with TestClient(create_app(store=store, clock=clock)) as client:
        payload = {
            "flight_id": "flt-100",
            "seat_id": "flt-100-1A",
            "passenger_name": "Ada Lovelace",
            "passenger_email": "ada@example.com",
        }
        assert client.post("/bookings/holds", json=payload).status_code == 201
        payload["seat_id"] = "flt-100-1B"
        duplicate = client.post("/bookings/holds", json=payload)
        assert duplicate.status_code == 409
        assert duplicate.json()["error"] == "duplicate_reservation"
        missing = client.get("/bookings/missing")
        assert missing.status_code == 404
        assert missing.json()["error"] == "booking_not_found"


def test_hold_duration_is_visible(clock, store: BookingStore) -> None:
    with TestClient(create_app(store=store, clock=clock, hold_minutes=15)) as client:
        response = client.post(
            "/bookings/holds",
            json={
                "flight_id": "flt-100",
                "seat_id": "flt-100-1C",
                "passenger_name": "Ada Lovelace",
                "passenger_email": "ada@example.com",
            },
        )
        expires_at = response.json()["expires_at"]
        assert expires_at.startswith((clock.now() + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M"))
