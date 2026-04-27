from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, status


def require_role(role_name: str) -> Callable[[dict[str, Any], str | None], dict[str, Any]]:
    def checker(claims: dict[str, Any], tenant_id: str | None = None) -> dict[str, Any]:
        membership = claims.get("active_membership")
        if not isinstance(membership, dict):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active membership is required.",
            )

        if tenant_id is not None and membership.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Membership for tenant '{tenant_id}' is required.",
            )
        if role_name in membership.get("roles", []):
            return membership

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role_name}' is required.",
        )

    return checker


def require_membership(tenant_id: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def checker(claims: dict[str, Any]) -> dict[str, Any]:
        membership = claims.get("active_membership")
        if isinstance(membership, dict) and membership.get("tenant_id") == tenant_id:
            return membership

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Membership for tenant '{tenant_id}' is required.",
        )

    return checker
