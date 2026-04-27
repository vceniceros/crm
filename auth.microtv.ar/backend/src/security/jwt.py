from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from jwt import InvalidTokenError

from src.config import settings


def _build_registered_claims(audience: str, expires_in_minutes: int) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "iss": settings.jwt_issuer,
        "aud": audience,
        "iat": now,
        "exp": now + timedelta(minutes=expires_in_minutes),
    }


def _normalize_active_membership(active_membership: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(active_membership, dict):
        raise ValueError("Active membership must be an object.")
    if "membership_id" not in active_membership:
        raise ValueError("Active membership id is required.")
    if "tenant_type" not in active_membership:
        raise ValueError("Active membership tenant_type is required.")
    if "tenant_id" not in active_membership:
        raise ValueError("Active membership tenant_id is required.")

    roles = active_membership.get("roles", [])
    if not isinstance(roles, list):
        raise ValueError("Active membership roles must be a list.")

    return {
        "membership_id": active_membership["membership_id"],
        "tenant_type": active_membership["tenant_type"],
        "tenant_id": active_membership["tenant_id"],
        "roles": [str(role) for role in roles],
    }


def create_access_token(user: Any, active_membership: dict[str, Any]) -> str:
    payload: dict[str, Any] = {
        "sub": user.user_id,
        "email": user.email,
        "active_membership": _normalize_active_membership(active_membership),
        **_build_registered_claims(settings.jwt_audience, settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user: Any, active_membership: dict[str, Any]) -> str:
    payload: dict[str, Any] = {
        "sub": user.user_id,
        "email": user.email,
        "active_membership": _normalize_active_membership(active_membership),
        **_build_registered_claims(f"{settings.jwt_issuer}:refresh", settings.refresh_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_login_ticket(user: Any) -> str:
    payload: dict[str, Any] = {
        "sub": user.user_id,
        "email": user.email,
        "jti": str(uuid4()),
        **_build_registered_claims(f"{settings.jwt_issuer}:context-selection", settings.login_ticket_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, audience: str | None = None) -> dict[str, Any]:
    decode_kwargs: dict[str, Any] = {
        "key": settings.jwt_secret,
        "algorithms": [settings.jwt_algorithm],
        "issuer": settings.jwt_issuer,
        "options": {
            "verify_aud": audience is not None,
            "verify_exp": True,
        },
    }
    if audience is not None:
        decode_kwargs["audience"] = audience

    return jwt.decode(
        token,
        **decode_kwargs,
    )


def validate_token(token: str) -> dict[str, Any]:
    try:
        payload = decode_token(token, audience=settings.jwt_audience)
    except InvalidTokenError as exc:
        raise ValueError("Invalid token.") from exc

    if not payload.get("sub"):
        raise ValueError("Token subject is required.")
    if not payload.get("email"):
        raise ValueError("Token email is required.")
    if "iat" not in payload:
        raise ValueError("Token issued-at claim is required.")
    if "exp" not in payload:
        raise ValueError("Token expiration claim is required.")
    if "aud" not in payload:
        raise ValueError("Token audience claim is required.")

    active_membership = payload.get("active_membership")
    payload["active_membership"] = _normalize_active_membership(active_membership)
    return payload


def validate_login_ticket(ticket: str) -> dict[str, Any]:
    try:
        payload = decode_token(ticket, audience=f"{settings.jwt_issuer}:context-selection")
    except InvalidTokenError as exc:
        raise ValueError("Invalid login ticket.") from exc

    jti = payload.get("jti")
    if not jti:
        raise ValueError("Login ticket id is required.")
    if not payload.get("sub"):
        raise ValueError("Login ticket subject is required.")
    if not payload.get("email"):
        raise ValueError("Login ticket email is required.")
    if "iat" not in payload:
        raise ValueError("Login ticket issued-at claim is required.")
    if "exp" not in payload:
        raise ValueError("Login ticket expiration claim is required.")
    return payload
