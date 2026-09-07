"""Thin wrapper around the upstream billing provider's HTTP API."""

import logging
import os

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 10


def fetch_user(user_id: str) -> dict:
    """Fetch a user record from the billing provider."""
    api_key = os.environ["BILLING_API_KEY"]
    try:
        response = requests.get(
            f"https://api.billing.example.com/users/{user_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("failed to fetch user %s: %s", user_id, exc)
        raise
    return response.json()
