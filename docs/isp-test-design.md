# Input space partitioning

This note records how the booking inputs were partitioned and which pytest functions represent each block. It is a test-design record for the team, not a claim that every combination was run.

## Approach

The interface under test is `BookingService`: `hold_seat`, `confirm_booking`, `cancel_booking`, and `get_booking`. Characteristics come from the arguments those methods actually branch on, plus the seat state and booking state those arguments meet.

Each characteristic is split into blocks the code treats differently. A block is represented by one value unless the comparison itself is the rule, which is the case for name length and hold expiry. Most tests are a valid base booking with one characteristic moved into another block. They are not the full Cartesian product of the blocks. Where two blocks interact and the implementation defines an order, that order has its own row.

HTTP tests are cited only when they are the representative for a block. The service tests are the ones that should stay aligned with this design.

Name length is counted after `normalize_name` collapses whitespace. A hold is active only while `now < expires_at`. `now == expires_at` is already expired. The test clock starts at 2026-11-08 12:00 UTC and the hold length is 15 minutes, so the deadline in these tests is 12:15:00.

## Hold a seat

| Characteristic | Block | Representative | Expected | Test |
| --- | --- | --- | --- | --- |
| Flight id | Known flight | `flt-100` | Hold is created | `test_hold_confirm_and_block_second_reservation` |
| Flight id | Unknown flight | `missing` | `FlightNotFound`; seat stays available and no booking is stored | `test_hold_unknown_flight_does_not_reserve_a_seat` |
| Flight id | Blank after trimming | `" "` | `InvalidRequest` | `test_passenger_validation` |
| Seat id | Seat on that flight | `flt-100-1A` | Hold is created | `test_hold_confirm_and_block_second_reservation` |
| Seat id | Seat on a different flight | `flt-200-1A` with flight `flt-100` | `SeatNotFound` | `test_seat_on_another_flight_is_not_found` |
| Seat id | Unknown seat | `missing` | `SeatNotFound` | `test_unknown_flight_and_seat` |
| Seat id | Blank after trimming | `"   "` | `InvalidRequest`; no booking is stored | `test_blank_seat_id_is_rejected` |
| Seat state | Available | `flt-100-1A` before any hold | Status `held` | `test_hold_confirm_and_block_second_reservation` |
| Seat state | Held by another passenger | second hold of `flt-100-1A` | `SeatUnavailable` (HTTP 409 `seat_unavailable`) | `test_http_booking_flow`; also `test_only_one_concurrent_hold_wins` |
| Seat state | Booked | `flt-100-1A` after confirm | `SeatUnavailable` | `test_hold_confirm_and_block_second_reservation` |
| Passenger already active, and the seat is also taken | Duplicate is checked first | same passenger and same held seat | `DuplicateReservation`, not `SeatUnavailable` | `test_duplicate_passenger_wins_over_unavailable_seat` |
| Passenger name | Empty after whitespace collapse | `"   "` | `InvalidRequest` | `test_passenger_validation` |
| Passenger name | Valid, with extra internal spaces | `"  Ada   Lovelace "` | Stored as `Ada Lovelace` | `test_hold_confirm_and_block_second_reservation` |
| Passenger name | Length 80 after normalization | 80 `A`s, padded with spaces | Hold stored with those 80 characters | `test_passenger_name_accepts_80_and_rejects_81` |
| Passenger name | Length 81 after normalization | 81 `B`s | `InvalidRequest`; the other seat stays available | `test_passenger_name_accepts_80_and_rejects_81` |
| Email | Valid, different case | `Ada@Example.com` | Stored as `ada@example.com` | `test_hold_confirm_and_block_second_reservation` |
| Email | Invalid format | `not-an-email` | `InvalidRequest`; HTTP 422 on the route | `test_passenger_validation`, `test_http_booking_flow` |
| Email | Already active on this flight | second seat, same email | `DuplicateReservation` | `test_hold_confirm_and_block_second_reservation`, `test_duplicate_reservation_http_code` |
| Email | Active booking was cancelled, expired, or `payment_failed` | same email again | A new hold is allowed | `test_cancel_hold_and_confirmed_booking`, `test_expired_hold_is_not_charged`, `test_decline_tokens_release_the_seat` |
| Email | Active on a different flight | `flt-200` while `flt-100` is held | Hold is created | `test_same_passenger_can_hold_a_seat_on_another_flight` |
| Invalid name while another hold is past its deadline | Validation runs before expiry | whitespace name, clock advanced 15 minutes | `InvalidRequest`; the elapsed hold stays `held` | `test_invalid_passenger_name_does_not_expire_elapsed_hold` |

## Confirm a booking

| Characteristic | Block | Representative | Expected | Test |
| --- | --- | --- | --- | --- |
| Payment token | Non-empty and not a decline token | `ok`, `tok_123`, `4242` | Status `confirmed`, seat `booked`, a reference is stored | `test_hold_confirm_and_block_second_reservation`, `test_hold_still_confirms_one_second_before_expiry`, `test_decline_tokens_and_amount` |
| Payment token | Decline token, case ignored | `FAIL`, `declined`, `insufficient_funds` | `PaymentFailedError`; booking `payment_failed`; seat available. A later confirm is `InvalidTransition` | `test_decline_tokens_release_the_seat`, `test_cancel_expired_or_failed_booking_is_rejected`, `test_http_booking_flow`, `test_decline_tokens_and_amount` |
| Payment token | Blank after trimming, hold still inside the window | `"   "` | `InvalidRequest`; booking stays `held` and the seat stays `held` | `test_blank_payment_token_does_not_change_the_hold` |
| Payment token | Blank after trimming, and `now == expires_at` | `"   "` after `clock.advance(minutes=15)` | `InvalidRequest`. Expiry does not run, so the booking stays `held` | `test_blank_payment_token_does_not_expire_elapsed_hold` |
| Price | Positive price copied at hold time | seed seat price, including 25000 on `flt-100-1A` | Charge uses that amount | `test_http_booking_flow` |
| Price | Non-positive | `price_cents == 0` with token `ok` | `PaymentFailedError` reason `invalid_amount`; seat released | `test_non_positive_amount_is_a_payment_failure`, `test_decline_tokens_and_amount` |
| Expiry | One second before the deadline | `advance(minutes=15, seconds=-1)` | Confirm succeeds. `is_active_reservation` is true for `expires_at == now + 1 second` | `test_hold_still_confirms_one_second_before_expiry`, `test_hold_is_active_before_expiry` |
| Expiry | Exactly at the deadline | `advance(minutes=15)`, so `now == expires_at` | `HoldExpired`. The gateway is not called. Seat becomes available. The same passenger can hold it again | `test_expired_hold_is_not_charged`, `test_hold_is_inactive_at_expiry_boundary` |
| Expiry | Missing `expires_at` | stored hold with `expires_at=None` | `HoldExpired`; seat released | `test_missing_expiry_is_treated_as_expired`, `test_hold_without_expiry_is_inactive` |
| Booking status | Already confirmed | second confirm | HTTP 409 `invalid_transition`. Concurrent confirms allow one winner | `test_http_booking_flow`, `test_only_one_concurrent_confirm_wins` |
| Booking status | `payment_failed` | confirm again with `ok` | `InvalidTransition` | `test_decline_tokens_release_the_seat` |
| Booking status | Seat no longer points at this hold | seat `booking_id` replaced with `other` | `InvalidTransition`; booking stays `held` | `test_confirm_rejects_a_seat_that_no_longer_matches_the_hold` |
| Booking id | Unknown | `get_booking("missing")` only | `BookingNotFound` | `test_passenger_validation` |

`now > expires_at` uses the same expired block as `now == expires_at`. `test_expiry_does_not_release_a_seat_owned_by_another_booking` advances 16 minutes, so it does execute the strict-after side, but that test is about leaving another booking's seat alone. It is not a separate expected outcome for the passenger.

## Cancel and read

| Characteristic | Block | Representative | Expected | Test |
| --- | --- | --- | --- | --- |
| Cancel | Status `held` | fresh hold | `cancelled`; seat available; a second cancel is `InvalidTransition` | `test_cancel_hold_and_confirmed_booking` |
| Cancel | Status `confirmed` | after `ok` | `cancelled`; seat available; the passenger can hold a different seat | `test_cancel_hold_and_confirmed_booking` |
| Cancel | Status `expired` at the deadline | `advance(minutes=15)` then cancel | `HoldExpired` | `test_cancel_expired_or_failed_booking_is_rejected` |
| Cancel | Status `payment_failed` | token `declined` | `InvalidTransition` | `test_cancel_expired_or_failed_booking_is_rejected` |
| Read | Past the deadline | `get_booking` after 15 minutes | Response status `expired`; a later sweep expires 0 | `test_get_booking_expires_lazily`, `test_get_booking_reports_expiry` |
| Read | Unknown id | `missing` | `BookingNotFound`; HTTP 404 | `test_passenger_validation`, `test_duplicate_reservation_http_code` |

Terminal statuses are not active reservations even when `expires_at` is still in the future: `test_terminal_statuses_are_not_active`. A confirmed booking stays active after the hold window: `test_confirmed_reservation_stays_active_after_hold_window`.

## Partitions not covered

These blocks are real, and this run did not give them a test:

- Confirm a `cancelled` booking. Cancel is tested, and confirming a `payment_failed` booking is tested, but confirm-after-cancel is not.
- `confirm_booking` or `cancel_booking` with an unknown booking id. Unknown ids are tested on `get_booking` and on `GET /bookings/missing` only.
- A negative `price_cents`. Zero is the representative for `amount_cents <= 0`. Negative was not executed.
- The empty payment string `""` on the service. The blank block is represented by `"   "`, which is empty after `strip`. Pydantic's `min_length=1` and the schema's own blank check are not what the service tests call.
- An empty or whitespace-only email. The invalid-email block is represented by `not-an-email`.
- `BookingService(..., hold_minutes=0)`. The constructor rejects a non-positive duration, and no test calls it.
- `get_flight` on a flight that exists. Unknown flights are tested; the successful return is only reached through other methods.
- HTTP requests that fail inside the schema for a blank seat id or a whitespace payment token. The service tests cover those values directly.
- Pairwise combinations beyond the rows above. For example, an 81-character name was not also combined with an unknown flight, and each decline token was not repeated at the one-second-before-expiry boundary.

Concurrency is covered by `tests/test_concurrency.py`, but it is not part of this partition. Those tests check locking, not another input block.

## Assumptions and limitations

- No authentication. The caller supplies the name and email.
- One active reservation per passenger per flight. Active means `confirmed`, or `held` with `now < expires_at`.
- Decline tokens are `fail`, `declined`, and `insufficient_funds`. Any other non-empty token succeeds. Nothing is sent to a payment provider.
- A declined charge is stored before `PaymentFailedError` is raised. The seat is released as part of that save.
- Invalid passenger input and a blank payment token return before `_expire_elapsed`, so they do not turn a due hold into `expired`.
- These tests run against PostgreSQL (the `booking_test` database), reset to `docs/seed.sql` before each test.
- Statement coverage from pytest-cov is a separate measurement. It does not mean the partitions above are complete. The uncovered rows in the previous section are still uncovered if the coverage percentage is high.
