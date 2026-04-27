from datetime import UTC, datetime, timedelta

import jwt
import pytest

from src.config import settings
from src.security import jwt as jwt_module


def test_decode_token_enforces_expiration_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_kwargs: dict[str, object] = {}

    def fake_decode(token: str, **kwargs: object) -> dict[str, object]:
        captured_kwargs.update(kwargs)
        return {
            "sub": "user-1",
            "email": "user@example.com",
            "jti": "ticket-1",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(minutes=1)).timestamp()),
        }

    monkeypatch.setattr(jwt_module.jwt, "decode", fake_decode)

    jwt_module.decode_token("token", audience=f"{settings.jwt_issuer}:context-selection")

    options = captured_kwargs["options"]
    assert isinstance(options, dict)
    assert options["verify_exp"] is True
    assert options["verify_aud"] is True


def test_validate_login_ticket_rejects_expired_token() -> None:
    payload = {
        "sub": "user-1",
        "email": "user@example.com",
        "jti": "ticket-1",
        "iss": settings.jwt_issuer,
        "aud": f"{settings.jwt_issuer}:context-selection",
        "iat": datetime.now(UTC) - timedelta(minutes=5),
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    with pytest.raises(ValueError, match="Invalid login ticket."):
        jwt_module.validate_login_ticket(token)
