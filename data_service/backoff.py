"""Exponential backoff for outbound calls to rate-limited upstream APIs.

Retries HTTP 429 (respecting a Retry-After header when the upstream sends
one), 5xx server errors, and connection/timeout failures using full-jitter
exponential backoff. Any other 4xx response is not retried -- a bad request
or a missing resource won't succeed on a retry, so failing fast there avoids
masking a real bug behind retry noise.
"""
from __future__ import annotations

import logging
import random
import time

import requests

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_DELAY_SECONDS = 0.5
DEFAULT_MAX_DELAY_SECONDS = 30.0
DEFAULT_TIMEOUT_SECONDS = 15.0


class UpstreamError(Exception):
    """Raised when an upstream API call exhausts all retry attempts."""


def request_with_backoff(
    method: str,
    url: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY_SECONDS,
    max_delay: float = DEFAULT_MAX_DELAY_SECONDS,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    **kwargs,
) -> requests.Response:
    """``requests.request(...)`` with exponential backoff + jitter on retryable failures."""
    attempt = 0
    while True:
        try:
            response = requests.request(method, url, timeout=timeout, **kwargs)
        except requests.RequestException as exc:
            attempt += 1
            if attempt > max_retries:
                raise UpstreamError(f"{method} {url} failed after {max_retries} retries: {exc}") from exc
            delay = _backoff_delay(attempt, base_delay, max_delay)
            logger.warning("Retrying %s %s (attempt %d/%d) after %.2fs -- %s", method, url, attempt, max_retries, delay, exc)
            time.sleep(delay)
            continue

        if response.status_code not in RETRYABLE_STATUS_CODES:
            return response

        attempt += 1
        if attempt > max_retries:
            raise UpstreamError(f"{method} {url} still returning {response.status_code} after {max_retries} retries")

        delay = _retry_delay(response, attempt, base_delay, max_delay)
        logger.warning(
            "Retrying %s %s (attempt %d/%d) after %.2fs -- upstream returned %d",
            method, url, attempt, max_retries, delay, response.status_code,
        )
        time.sleep(delay)


def _retry_delay(response: requests.Response, attempt: int, base_delay: float, max_delay: float) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        try:
            return float(retry_after)
        except ValueError:
            pass
    return _backoff_delay(attempt, base_delay, max_delay)


def _backoff_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    """Full-jitter exponential backoff: a random delay in [0, min(cap, base * 2^(attempt-1))]."""
    ceiling = min(base_delay * (2 ** (attempt - 1)), max_delay)
    return random.uniform(0, ceiling)
