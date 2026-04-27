"""
Extended pytest suite for the login_ticket flow.

These tests exercise the expiration, stress, and optional multi-instance
scenarios that are not covered by test_login_ticket_audit.py.

Run the full suite (including slow tests):
    pytest backend/tests/ -v

Run only fast tests (skip slow markers):
    pytest backend/tests/ -v -m "not slow"

Environment variables:
    AUTH_BASE_URL                      default: http://127.0.0.1:8001
    AUTH_DB_URL                        default: postgresql://microtv:microtv@localhost/auth_microtv
    AUTH_INSTANCE_URLS                 comma-separated list for multi-instance probe
    LOGIN_TICKET_STRESS_ITERATIONS     default: 1000
    LOGIN_TICKET_CONCURRENCY_REQUESTS  default: 100
    LOGIN_TICKET_CONCURRENCY_WORKERS   default: 50
"""

import pytest

from login_ticket_audit_runner import (
    default_membership_id,
    execute_expiration_probe,
    login_multi_tenant,
    prepare_expiration_probe,
    run_multi_instance_probe,
    run_psql,
    run_stress_test,
    select_context,
)


# ---------------------------------------------------------------------------
# Expiration – ticket rejected after expires_at is in the past (DB shortcut)
# ---------------------------------------------------------------------------

def test_login_ticket_expiration_db() -> None:
    """
    Issue a login ticket, force-expire it via a direct DB UPDATE, then confirm
    that POST /v1/auth/select-context returns HTTP 401.

    This test does NOT wait for the natural JWT TTL. Instead it updates the
    login_ticket row so that expires_at is in the past and verifies that the
    atomic UPDATE inside consume_login_ticket uses the expires_at > now()
    condition correctly.

    Note: JWT signature validation in validate_login_ticket() also rejects
    expired tokens, so two independent layers of expiration protection are
    exercised here. The JWT will still be valid from PyJWT's perspective
    because we manipulate only the DB column, not the JWT payload, which
    means we specifically test the DB-level guard.
    """
    login_result = login_multi_tenant()
    assert login_result.status_code == 200, (
        f"Login failed: {login_result.status_code} {login_result.body_text[:200]}"
    )
    login_body = login_result.json_body
    ticket = login_body.get("login_ticket", "")
    membership_id = default_membership_id(login_body)

    assert ticket, "Login did not return a login_ticket"

    # Force the ticket to be expired in the DB without touching the JWT payload.
    # This specifically exercises the DB-level guard inside consume_login_ticket():
    #   LoginTicket.expires_at > func.now()
    # The JWT itself remains cryptographically valid (exp is still in the future),
    # so only the DB check triggers the rejection.
    run_psql(
        "UPDATE login_tickets "
        "SET expires_at = NOW() - INTERVAL '1 minute' "
        "WHERE user_id = '11111111-1111-4111-8111-111111111111' "
        "  AND consumed_at IS NULL;"
    )

    result = select_context(ticket, membership_id)
    assert result.status_code == 401, (
        f"Expected 401 after DB expiration, got {result.status_code}: "
        f"{result.body_text[:200]}"
    )


# ---------------------------------------------------------------------------
# Expiration – full natural wait (slow; skipped in quick runs)
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_login_ticket_expiration_natural_wait() -> None:
    """
    Issue a login ticket and wait until the JWT itself expires, then verify
    HTTP 401.  This test takes as long as LOGIN_TICKET_EXPIRE_MINUTES (default
    10 minutes) and is therefore marked slow.
    """
    probe = prepare_expiration_probe()
    assert probe["login_status"] == 200, (
        f"Login failed before expiration probe: {probe['login_status']}"
    )
    result = execute_expiration_probe(probe)
    assert result["pass"], (
        f"Expected 401 after natural expiration (waited {result['wait_seconds']}s), "
        f"got {result['select_status_after_expiration']}: "
        f"{result['select_body_after_expiration']}"
    )


# ---------------------------------------------------------------------------
# Stress – 1 000 full login → select-context iterations
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_login_ticket_stress() -> None:
    """
    Run LOGIN_TICKET_STRESS_ITERATIONS (default: 1 000) consecutive
    login → select-context → replay-attempt cycles.

    Pass criteria:
    - Every first select-context succeeds (HTTP 200).
    - Zero replay successes (strict one-time-use enforcement).
    """
    result = run_stress_test()

    assert result["replay_success_count"] == 0, (
        f"CRITICAL: {result['replay_success_count']} replay(s) succeeded across "
        f"{result['iterations']} iterations. "
        f"Sample anomalies: {result['anomalies_sample'][:5]}"
    )
    assert result["first_select_success"] == result["iterations"], (
        f"Expected all {result['iterations']} first-select calls to succeed, "
        f"but only {result['first_select_success']} did. "
        f"Anomalies: {result['anomalies_count']} — sample: {result['anomalies_sample'][:5]}"
    )


# ---------------------------------------------------------------------------
# Multi-instance – two auth nodes sharing the same PostgreSQL database
# ---------------------------------------------------------------------------

def test_login_ticket_multi_instance() -> None:
    """
    When AUTH_INSTANCE_URLS contains two comma-separated base URLs, issues one
    login ticket through the primary instance and confirms that exactly one of
    the two instances can consume it (the other must return HTTP 401).

    If fewer than two URLs are configured, the test is skipped automatically.
    """
    result = run_multi_instance_probe()

    if not result["executed"]:
        pytest.skip(result["reason"])

    assert result["pass"], (
        f"Multi-instance consumption breach: "
        f"primary={result['primary_select_status']}, "
        f"secondary={result['secondary_select_status']}. "
        f"Expected exactly one 200 and one 401."
    )
