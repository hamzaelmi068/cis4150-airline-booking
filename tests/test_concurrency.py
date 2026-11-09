import threading

from app.domain.enums import BookingStatus, SeatStatus
from app.domain.errors import DuplicateReservation, InvalidTransition, SeatUnavailable
from app.services.booking_service import BookingService


def _run(workers: list) -> None:
    threads = [threading.Thread(target=worker) for worker in workers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def test_only_one_concurrent_hold_wins(service: BookingService, store) -> None:
    barrier = threading.Barrier(8)
    results: list[str] = []
    results_lock = threading.Lock()

    def attempt(index: int) -> None:
        barrier.wait()
        try:
            service.hold_seat(
                "flt-100",
                "flt-100-1A",
                f"Passenger {index}",
                f"p{index}@example.com",
            )
            outcome = "ok"
        except SeatUnavailable:
            outcome = "unavailable"
        with results_lock:
            results.append(outcome)

    _run([lambda index=index: attempt(index) for index in range(8)])
    assert results.count("ok") == 1
    assert results.count("unavailable") == 7
    assert store.get_seat("flt-100-1A").status == SeatStatus.HELD


def test_concurrent_holds_for_one_passenger_allow_one(service: BookingService) -> None:
    barrier = threading.Barrier(2)
    results: list[str] = []
    results_lock = threading.Lock()

    def attempt(seat_id: str) -> None:
        barrier.wait()
        try:
            service.hold_seat("flt-100", seat_id, "Ada Lovelace", "ada@example.com")
            outcome = "ok"
        except DuplicateReservation:
            outcome = "duplicate"
        with results_lock:
            results.append(outcome)

    _run(
        [
            lambda: attempt("flt-100-1A"),
            lambda: attempt("flt-100-1B"),
        ]
    )
    assert sorted(results) == ["duplicate", "ok"]


def test_only_one_concurrent_confirm_wins(service: BookingService, store) -> None:
    booking = service.hold_seat("flt-100", "flt-100-1A", "Ada Lovelace", "ada@example.com")
    barrier = threading.Barrier(6)
    results: list[str] = []
    results_lock = threading.Lock()

    def attempt() -> None:
        barrier.wait()
        try:
            service.confirm_booking(booking.id, "ok")
            outcome = "ok"
        except InvalidTransition:
            outcome = "invalid"
        with results_lock:
            results.append(outcome)

    _run([attempt for _ in range(6)])
    assert results.count("ok") == 1
    assert results.count("invalid") == 5
    saved = store.get_booking(booking.id)
    assert saved.status == BookingStatus.CONFIRMED
    assert store.get_seat("flt-100-1A").status == SeatStatus.BOOKED
    assert saved.confirmation_code is not None
