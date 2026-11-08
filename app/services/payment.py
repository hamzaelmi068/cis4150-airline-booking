from dataclasses import dataclass
from typing import Protocol

# These tokens always decline. Any other non-empty token succeeds.
# Comparison is case-insensitive. This keeps payment tests deterministic.
DECLINE_TOKENS = frozenset({"fail", "declined", "insufficient_funds"})


@dataclass(frozen=True)
class PaymentResult:
    success: bool
    reference: str | None
    reason: str | None


class PaymentGateway(Protocol):
    def charge(
        self,
        *,
        amount_cents: int,
        payment_token: str,
        booking_id: str,
    ) -> PaymentResult:
        """Simulate a charge. No external payment provider is contacted."""


class SimulatedPaymentGateway:
    def charge(
        self,
        *,
        amount_cents: int,
        payment_token: str,
        booking_id: str,
    ) -> PaymentResult:
        if amount_cents <= 0:
            return PaymentResult(False, None, "invalid_amount")
        token = payment_token.strip().lower()
        if token in DECLINE_TOKENS:
            return PaymentResult(False, None, token)
        return PaymentResult(True, f"sim_{booking_id[:8]}", None)
