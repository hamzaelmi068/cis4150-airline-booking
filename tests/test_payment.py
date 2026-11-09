from app.services.payment import DECLINE_TOKENS, SimulatedPaymentGateway


def test_decline_tokens_and_amount() -> None:
    gateway = SimulatedPaymentGateway()
    for token in DECLINE_TOKENS:
        result = gateway.charge(amount_cents=100, payment_token=token.upper(), booking_id="booking-1")
        assert not result.success
        assert result.reason == token
    success = gateway.charge(amount_cents=100, payment_token="4242", booking_id="booking-12345678")
    assert success.success
    assert success.reference == "sim_booking-"
    invalid = gateway.charge(amount_cents=0, payment_token="ok", booking_id="booking-1")
    assert invalid.reason == "invalid_amount"
