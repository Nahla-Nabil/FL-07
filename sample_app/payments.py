"""Payment charge/refund helpers for the checkout flow."""

import logging

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """Raised when a payment operation fails."""


def charge_card(account_id: str, amount_cents: int) -> str:
    """Charge a card and return the resulting transaction id."""
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    try:
        transaction_id = _submit_charge(account_id, amount_cents)
    except PaymentError as exc:
        logger.error("charge failed for %s: %s", account_id, exc)
        raise
    return transaction_id


def _submit_charge(account_id: str, amount_cents: int) -> str:
    """Placeholder for the real gateway call."""
    return f"txn_{account_id}_{amount_cents}"
