"""PaymentProvider: the mock provider is the default, Razorpay test mode is Day 3.

No real money moves through this app. A provider only ever reports a status.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import uuid4

import config


@dataclass(frozen=True)
class PaymentResult:
    provider_ref: str
    status: str  # paid | pending | failed


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def create_payment(self, *, order_id: int, amount_inr: int) -> PaymentResult:
        """Start a payment for an order. Mock returns a pending reference."""

    @abstractmethod
    def confirm_payment(self, *, provider_ref: str) -> PaymentResult:
        """Settle a payment. Mock always succeeds."""


class MockProvider(PaymentProvider):
    name = "mock"

    def create_payment(self, *, order_id: int, amount_inr: int) -> PaymentResult:
        return PaymentResult(provider_ref=f"mock_{order_id}_{uuid4().hex[:8]}", status="pending")

    def confirm_payment(self, *, provider_ref: str) -> PaymentResult:
        return PaymentResult(provider_ref=provider_ref, status="paid")


class RazorpayProvider(PaymentProvider):
    """Test mode only, and only once Day 3 wires it up."""

    name = "razorpay"

    def __init__(self) -> None:
        if not config.RAZORPAY_KEY_ID or not config.RAZORPAY_KEY_SECRET:
            raise RuntimeError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are required")

    def create_payment(self, *, order_id: int, amount_inr: int) -> PaymentResult:
        raise NotImplementedError("Razorpay test mode is scheduled for Day 3")

    def confirm_payment(self, *, provider_ref: str) -> PaymentResult:
        raise NotImplementedError("Razorpay test mode is scheduled for Day 3")


def get_provider() -> PaymentProvider:
    """The provider named by PAYMENT_PROVIDER, defaulting to the mock."""
    if config.PAYMENT_PROVIDER == "razorpay":
        return RazorpayProvider()
    return MockProvider()
