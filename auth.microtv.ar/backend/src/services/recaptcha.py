import logging

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

_RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


async def verify_recaptcha(token: str, action: str = "") -> float:
    """
    Verify a reCAPTCHA v3 token against Google's API.

    Returns the score (0.0–1.0) on success.
    Raises ValueError if the verification fails or the score is below the
    configured minimum threshold.

    If RECAPTCHA_SECRET_KEY is empty (dev/test mode), bypasses verification
    and returns 1.0.
    """
    if not settings.recaptcha_secret_key:
        logger.warning("RECAPTCHA_SECRET_KEY not set — bypassing reCAPTCHA verification (dev mode).")
        return 1.0

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                _RECAPTCHA_VERIFY_URL,
                data={"secret": settings.recaptcha_secret_key, "response": token},
            )
            response.raise_for_status()
            result: dict = response.json()
    except httpx.HTTPError as exc:
        logger.error("reCAPTCHA HTTP error: %s", exc)
        raise ValueError("reCAPTCHA verification failed.") from exc

    if not result.get("success"):
        error_codes = result.get("error-codes", [])
        logger.warning("reCAPTCHA rejected: %s", error_codes)
        raise ValueError("reCAPTCHA verification failed.")

    score = float(result.get("score", 0.0))
    if score < settings.recaptcha_min_score:
        logger.warning(
            "reCAPTCHA score %.2f is below minimum %.2f (action=%r)",
            score,
            settings.recaptcha_min_score,
            action,
        )
        raise ValueError("reCAPTCHA score too low.")

    return score
