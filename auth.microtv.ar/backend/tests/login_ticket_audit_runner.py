import base64
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_URL = os.getenv("AUTH_BASE_URL", "http://127.0.0.1:8001")
DB_URL = os.getenv("AUTH_DB_URL", "postgresql://microtv:microtv@localhost/auth_microtv")
REPORT_PATH = Path(os.getenv("LOGIN_TICKET_REPORT_PATH", "docs/tests/2026-login-ticket-audit.md"))
ITERATIONS = int(os.getenv("LOGIN_TICKET_STRESS_ITERATIONS", "1000"))
CONCURRENCY_REQUESTS = int(os.getenv("LOGIN_TICKET_CONCURRENCY_REQUESTS", "100"))
CONCURRENCY_WORKERS = int(os.getenv("LOGIN_TICKET_CONCURRENCY_WORKERS", "50"))
HTTP_TIMEOUT_SECONDS = float(os.getenv("LOGIN_TICKET_HTTP_TIMEOUT_SECONDS", "20"))
INSTANCE_URLS = [
    url.strip()
    for url in os.getenv("AUTH_INSTANCE_URLS", "").split(",")
    if url.strip()
]

AUDIT_USER = {
    "user_id": "11111111-1111-4111-8111-111111111111",
    "email": "audit.login.ticket@test.com",
    "password": "admin123",
    "display_name": "Audit User",
    "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$JlfQehh+qBko/JxtHPdJEQ$ScUMHfbcgAoN1EXNhsSmEIyA4y/PTiYy1GVG5bM3zb4",
}
AUDIT_MEMBERSHIPS = [
    {
        "membership_id": "22222222-2222-4222-8222-222222222221",
        "tenant_type": "company",
        "tenant_id": "company_audit_1",
        "assignment_id": "audit-assign-00000000000000000000001",
    },
    {
        "membership_id": "22222222-2222-4222-8222-222222222222",
        "tenant_type": "company",
        "tenant_id": "company_audit_2",
        "assignment_id": "audit-assign-00000000000000000000002",
    },
]
VIEWER_ROLE = {
    "role_id": "role-viewer-00000000000000000000001",
    "role_name": "viewer",
    "description": "Read-only role",
}


@dataclass
class HttpResult:
    status_code: int
    body_text: str
    latency_ms: float

    @property
    def json_body(self) -> dict[str, Any]:
        try:
            return json.loads(self.body_text)
        except json.JSONDecodeError:
            return {}


def http_request(
    path: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    base_url: str = BASE_URL,
    timeout_seconds: float = HTTP_TIMEOUT_SECONDS,
) -> HttpResult:
    data = None
    headers = {"content-type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            latency_ms = (time.perf_counter() - start) * 1000
            return HttpResult(response.getcode(), response.read().decode("utf-8", errors="replace"), latency_ms)
    except urllib.error.HTTPError as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        body_text = exc.read().decode("utf-8", errors="replace")
        exc.close()
        return HttpResult(exc.code, body_text, latency_ms)


def decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8")
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return {}


def run_psql(sql: str) -> str:
    psql_binary = shutil.which("psql")
    if not psql_binary:
        raise FileNotFoundError("psql was not found on PATH.")

    completed = subprocess.run(
        [psql_binary, DB_URL, "-v", "ON_ERROR_STOP=1", "-X"],
        input=sql.encode("utf-8"),
        capture_output=True,
        check=True,
    )
    return completed.stdout.decode("utf-8", errors="replace")


def setup_audit_data() -> str:
    user = AUDIT_USER
    membership_1, membership_2 = AUDIT_MEMBERSHIPS
    role = VIEWER_ROLE
    sql = f"""
BEGIN;
DELETE FROM login_tickets
WHERE user_id IN (
    SELECT user_id FROM users WHERE email = '{user["email"]}'
    UNION
    SELECT '{user["user_id"]}'
);

DELETE FROM role_assignments
WHERE membership_id IN (
    SELECT membership_id
    FROM memberships
    WHERE user_id IN (
        SELECT user_id FROM users WHERE email = '{user["email"]}'
        UNION
        SELECT '{user["user_id"]}'
    )
);

DELETE FROM memberships
WHERE user_id IN (
    SELECT user_id FROM users WHERE email = '{user["email"]}'
    UNION
    SELECT '{user["user_id"]}'
);

DELETE FROM users
WHERE user_id = '{user["user_id"]}' OR email = '{user["email"]}';

INSERT INTO roles(role_id, role_name, description)
VALUES ('{role["role_id"]}', '{role["role_name"]}', '{role["description"]}')
ON CONFLICT (role_name) DO NOTHING;

INSERT INTO users(user_id, email, display_name, password_hash, status)
VALUES (
    '{user["user_id"]}',
    '{user["email"]}',
    '{user["display_name"]}',
    '{user["password_hash"]}',
    'active'
);

INSERT INTO memberships(membership_id, user_id, tenant_type, tenant_id)
VALUES
    ('{membership_1["membership_id"]}', '{user["user_id"]}', '{membership_1["tenant_type"]}', '{membership_1["tenant_id"]}'),
    ('{membership_2["membership_id"]}', '{user["user_id"]}', '{membership_2["tenant_type"]}', '{membership_2["tenant_id"]}');

INSERT INTO role_assignments(assignment_id, membership_id, role_id)
VALUES
    ('{membership_1["assignment_id"]}', '{membership_1["membership_id"]}', (SELECT role_id FROM roles WHERE role_name = '{role["role_name"]}')),
    ('{membership_2["assignment_id"]}', '{membership_2["membership_id"]}', (SELECT role_id FROM roles WHERE role_name = '{role["role_name"]}'));
COMMIT;
"""
    return run_psql(sql)


def login_multi_tenant(base_url: str = BASE_URL) -> HttpResult:
    return http_request(
        "/v1/auth/login",
        method="POST",
        body={"email": AUDIT_USER["email"], "password": AUDIT_USER["password"]},
        base_url=base_url,
    )


def select_context(login_ticket: str, membership_id: str, base_url: str = BASE_URL) -> HttpResult:
    return http_request(
        "/v1/auth/select-context",
        method="POST",
        body={"login_ticket": login_ticket, "membership_id": membership_id},
        base_url=base_url,
    )


def default_membership_id(login_body: dict[str, Any]) -> str:
    memberships = login_body.get("memberships") or []
    if memberships:
        return memberships[0]["membership_id"]
    return AUDIT_MEMBERSHIPS[0]["membership_id"]


def summarize_latencies(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    ordered = sorted(values)
    p95_index = int(0.95 * (len(ordered) - 1))
    return {
        "count": len(values),
        "avg_ms": round(statistics.mean(values), 2),
        "p95_ms": round(ordered[p95_index], 2),
        "max_ms": round(max(values), 2),
    }


def severity_rank(severity: str) -> int:
    order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    return order.get(severity, 0)


def add_anomaly(anomalies: list[dict[str, Any]], severity: str, title: str, details: str) -> None:
    anomalies.append({"severity": severity, "title": title, "details": details})


def sanitize_database_url(database_url: str) -> str:
    if "://" not in database_url or "@" not in database_url:
        return database_url
    scheme, remainder = database_url.split("://", 1)
    credentials, host = remainder.split("@", 1)
    if ":" not in credentials:
        return f"{scheme}://***@{host}"
    username, _password = credentials.split(":", 1)
    return f"{scheme}://{username}:***@{host}"


def run_replay_test() -> dict[str, Any]:
    login_result = login_multi_tenant()
    login_body = login_result.json_body
    ticket = login_body.get("login_ticket", "")
    membership_id = default_membership_id(login_body)
    first_select = select_context(ticket, membership_id)
    second_select = select_context(ticket, membership_id)
    return {
        "login_status": login_result.status_code,
        "first_select_status": first_select.status_code,
        "second_select_status": second_select.status_code,
        "first_select_body": first_select.body_text[:200],
        "second_select_body": second_select.body_text[:200],
        "pass": (
            login_result.status_code == 200
            and first_select.status_code == 200
            and second_select.status_code == 401
        ),
    }


def run_concurrency_test() -> dict[str, Any]:
    login_result = login_multi_tenant()
    login_body = login_result.json_body
    ticket = login_body.get("login_ticket", "")
    membership_id = default_membership_id(login_body)
    results: list[HttpResult] = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY_WORKERS) as executor:
        futures = [
            executor.submit(select_context, ticket, membership_id)
            for _ in range(CONCURRENCY_REQUESTS)
        ]
        for future in as_completed(futures):
            results.append(future.result())

    codes = [result.status_code for result in results]
    success_count = sum(1 for code in codes if code == 200)
    unauthorized_count = sum(1 for code in codes if code == 401)
    other_statuses = sorted({code for code in codes if code not in {200, 401}})
    return {
        "requests": CONCURRENCY_REQUESTS,
        "workers": CONCURRENCY_WORKERS,
        "login_status": login_result.status_code,
        "success_200": success_count,
        "unauthorized_401": unauthorized_count,
        "other_statuses": other_statuses,
        "pass": (
            login_result.status_code == 200
            and success_count == 1
            and unauthorized_count == CONCURRENCY_REQUESTS - 1
            and not other_statuses
        ),
    }


def prepare_expiration_probe() -> dict[str, Any]:
    login_result = login_multi_tenant()
    login_body = login_result.json_body
    ticket = login_body.get("login_ticket", "")
    membership_id = default_membership_id(login_body)
    payload = decode_jwt_payload(ticket)
    now_epoch = int(time.time())
    exp_epoch = int(payload.get("exp", now_epoch))
    wait_seconds = max(0, exp_epoch - now_epoch + 1)
    ready_at = time.time() + wait_seconds
    return {
        "login_status": login_result.status_code,
        "ticket": ticket,
        "membership_id": membership_id,
        "jwt_exp_epoch": exp_epoch,
        "wait_seconds": wait_seconds,
        "ready_at": ready_at,
    }


def execute_expiration_probe(probe: dict[str, Any]) -> dict[str, Any]:
    # Sleep in a loop to guard against time.sleep() returning early (observed on WSL2).
    while True:
        remaining = probe["ready_at"] - time.time()
        if remaining <= 0:
            break
        time.sleep(min(remaining, 30))
    select_result = select_context(probe["ticket"], probe["membership_id"])
    return {
        "login_status": probe["login_status"],
        "wait_seconds": probe["wait_seconds"],
        "jwt_exp_epoch": probe["jwt_exp_epoch"],
        "select_status_after_expiration": select_result.status_code,
        "select_body_after_expiration": select_result.body_text[:200],
        "pass": select_result.status_code == 401,
    }


def run_stress_test() -> dict[str, Any]:
    anomalies: list[dict[str, Any]] = []
    login_latencies: list[float] = []
    select_latencies: list[float] = []
    first_select_success = 0
    replay_success_count = 0

    for iteration in range(1, ITERATIONS + 1):
        login_result = login_multi_tenant()
        login_latencies.append(login_result.latency_ms)
        login_body = login_result.json_body
        if login_result.status_code != 200 or "login_ticket" not in login_body or not login_body.get("memberships"):
            anomalies.append(
                {
                    "iteration": iteration,
                    "phase": "login",
                    "status": login_result.status_code,
                    "body": login_result.body_text[:120],
                }
            )
            continue

        ticket = login_body["login_ticket"]
        membership_id = default_membership_id(login_body)
        first_select = select_context(ticket, membership_id)
        select_latencies.append(first_select.latency_ms)
        replay_select = select_context(ticket, membership_id)

        if first_select.status_code == 200:
            first_select_success += 1
        else:
            anomalies.append(
                {
                    "iteration": iteration,
                    "phase": "first_select",
                    "status": first_select.status_code,
                    "body": first_select.body_text[:120],
                }
            )

        if replay_select.status_code == 200:
            replay_success_count += 1
            anomalies.append(
                {
                    "iteration": iteration,
                    "phase": "replay_select",
                    "status": replay_select.status_code,
                    "body": replay_select.body_text[:120],
                }
            )
        elif replay_select.status_code != 401:
            anomalies.append(
                {
                    "iteration": iteration,
                    "phase": "replay_select",
                    "status": replay_select.status_code,
                    "body": replay_select.body_text[:120],
                }
            )

    return {
        "iterations": ITERATIONS,
        "first_select_success": first_select_success,
        "replay_success_count": replay_success_count,
        "anomalies_count": len(anomalies),
        "anomalies_sample": anomalies[:20],
        "latency_login": summarize_latencies(login_latencies),
        "latency_select": summarize_latencies(select_latencies),
        "pass": replay_success_count == 0 and first_select_success == ITERATIONS,
    }


def run_multi_instance_probe() -> dict[str, Any]:
    if len(INSTANCE_URLS) < 2:
        return {
            "executed": False,
            "reason": "Two auth instance URLs were not provided via AUTH_INSTANCE_URLS.",
        }

    primary, secondary = INSTANCE_URLS[:2]
    login_result = login_multi_tenant(base_url=primary)
    login_body = login_result.json_body
    ticket = login_body.get("login_ticket", "")
    membership_id = default_membership_id(login_body)
    first_select = select_context(ticket, membership_id, base_url=primary)
    second_select = select_context(ticket, membership_id, base_url=secondary)

    return {
        "executed": True,
        "primary_base_url": primary,
        "secondary_base_url": secondary,
        "login_status": login_result.status_code,
        "primary_select_status": first_select.status_code,
        "secondary_select_status": second_select.status_code,
        "pass": (
            login_result.status_code == 200
            and sorted([first_select.status_code, second_select.status_code]) == [200, 401]
        ),
    }


def build_verdict(anomalies: list[dict[str, Any]]) -> dict[str, str]:
    if not anomalies:
        return {
            "status": "PASS",
            "summary": "Replay, concurrency, expiration, and stress behavior matched the expected one-time consumption contract.",
        }

    highest = max(anomalies, key=lambda item: severity_rank(item["severity"]))
    if highest["severity"] == "CRITICAL":
        status = "FAIL"
    else:
        status = "PARTIAL PASS"

    return {
        "status": status,
        "summary": f'Highest observed severity: {highest["severity"]}.',
    }


def render_report(results: dict[str, Any]) -> str:
    environment = results["environment"]
    replay = results["tests"]["replay"]
    concurrency = results["tests"]["concurrency"]
    expiration = results["tests"]["expiration"]
    stress = results["tests"]["stress"]
    multi_instance = results["tests"]["multi_instance"]
    anomalies = results["anomalies"]
    verdict = results["verdict"]

    anomaly_lines = []
    if anomalies:
        for index, anomaly in enumerate(anomalies, start=1):
            anomaly_lines.append(f"### A{index} - {anomaly['title']}")
            anomaly_lines.append(f"- Severity: **{anomaly['severity']}**")
            anomaly_lines.append(f"- Evidence: {anomaly['details']}")
            anomaly_lines.append("")
    else:
        anomaly_lines.append("No anomalies were detected.")
        anomaly_lines.append("")

    if multi_instance["executed"]:
        multi_instance_lines = [
            "- Primary instance login status: `{}`".format(multi_instance["login_status"]),
            "- Primary instance select-context status: `{}`".format(multi_instance["primary_select_status"]),
            "- Secondary instance select-context status: `{}`".format(multi_instance["secondary_select_status"]),
            "- Result: `{}`".format("PASS" if multi_instance["pass"] else "FAIL"),
        ]
    else:
        multi_instance_lines = [f"- Not executed: {multi_instance['reason']}"]

    severity_counts = {
        severity: sum(1 for anomaly in anomalies if anomaly["severity"] == severity)
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    }
    dataset_reset_status = environment.get("dataset_reset_status", "not recorded")
    if dataset_reset_status == "executed":
        dataset_line = "The dataset was reset through PostgreSQL before execution so the same user and memberships were used across all scenarios."
    else:
        dataset_line = (
            "The PostgreSQL reset step was skipped because `psql` was unavailable in this shell; "
            "the audit used the already-seeded multi-tenant audit user present in the environment."
        )

    return f"""# 2026 Login Ticket Audit

## 1. Environment description

- Service URL: `{environment["service_url"]}`
- Health endpoint: `GET /health` -> `{environment["health_status"]}`
- Health body: `{environment["health_body"]}`
- Database URL: `{environment["database_url"]}`
- Login ticket TTL configured by service: `{environment["login_ticket_expire_minutes"]}` minutes
- Host platform: `{environment["platform"]}`
- Python runtime used for the audit harness: `{environment["python_version"]}`
- Audit dataset user: `{environment["audit_user_email"]}`

## 2. Test methodology

The audit used a controlled multi-tenant user persisted in PostgreSQL and exercised the production endpoints only:

1. `POST /v1/auth/login`
2. `POST /v1/auth/select-context`

Scenarios executed:

1. Replay: `login -> select-context -> select-context` using the same `login_ticket`
2. Concurrency: `{concurrency["requests"]}` parallel `select-context` requests against the same `login_ticket`
3. Expiration: `login -> wait until JWT exp -> select-context`
4. Stress: `{stress["iterations"]}` full iterations of `login -> select-context -> replay attempt`
5. Optional multi-instance probe when two base URLs are supplied via `AUTH_INSTANCE_URLS`

{dataset_line}

## 3. Replay results

- Login status: `{replay["login_status"]}`
- First `select-context`: `{replay["first_select_status"]}`
- Second `select-context` with the same ticket: `{replay["second_select_status"]}`
- Result: `{ "PASS" if replay["pass"] else "FAIL" }`

## 4. Concurrency results

- Parallel requests: `{concurrency["requests"]}`
- Worker threads: `{concurrency["workers"]}`
- Successful `200` responses: `{concurrency["success_200"]}`
- Unauthorized `401` responses: `{concurrency["unauthorized_401"]}`
- Other statuses: `{concurrency["other_statuses"]}`
- Result: `{ "PASS" if concurrency["pass"] else "FAIL" }`

## 5. Expiration results

- Login status: `{expiration["login_status"]}`
- Wait time until expiration: `{expiration["wait_seconds"]}` seconds
- `select-context` after expiration: `{expiration["select_status_after_expiration"]}`
- Result: `{ "PASS" if expiration["pass"] else "FAIL" }`

## 6. Stress results

- Iterations executed: `{stress["iterations"]}`
- First `select-context` successes: `{stress["first_select_success"]}`
- Replay successes detected: `{stress["replay_success_count"]}`
- Stress anomalies recorded: `{stress["anomalies_count"]}`
- Login latency: avg `{stress["latency_login"].get("avg_ms", "n/a")}` ms, p95 `{stress["latency_login"].get("p95_ms", "n/a")}` ms, max `{stress["latency_login"].get("max_ms", "n/a")}` ms
- Select-context latency: avg `{stress["latency_select"].get("avg_ms", "n/a")}` ms, p95 `{stress["latency_select"].get("p95_ms", "n/a")}` ms, max `{stress["latency_select"].get("max_ms", "n/a")}` ms
- Result: `{ "PASS" if stress["pass"] else "FAIL" }`

## 7. Optional multi-instance simulation

{chr(10).join(multi_instance_lines)}

## 8. Anomalies detected

{chr(10).join(anomaly_lines).rstrip()}

## 9. Final verdict

**Verdict: {verdict["status"]}**

{verdict["summary"]}

Severity summary:

- `CRITICAL`: {severity_counts["CRITICAL"]}
- `HIGH`: {severity_counts["HIGH"]}
- `MEDIUM`: {severity_counts["MEDIUM"]}
- `LOW`: {severity_counts["LOW"]}
"""


def run_audit() -> dict[str, Any]:
    results: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "service_url": BASE_URL,
            "database_url": sanitize_database_url(DB_URL),
            "platform": platform.platform(),
            "python_version": sys.version.split()[0],
            "audit_user_email": AUDIT_USER["email"],
            "login_ticket_expire_minutes": os.getenv("LOGIN_TICKET_EXPIRE_MINUTES", "10"),
        },
        "tests": {},
        "anomalies": [],
    }

    health = http_request("/health")
    results["environment"]["health_status"] = health.status_code
    results["environment"]["health_body"] = health.body_text
    results["environment"]["health_latency_ms"] = round(health.latency_ms, 2)
    try:
        results["environment"]["dataset_reset_stdout"] = setup_audit_data()
        results["environment"]["dataset_reset_status"] = "executed"
    except FileNotFoundError as exc:
        results["environment"]["dataset_reset_stdout"] = ""
        results["environment"]["dataset_reset_status"] = f"skipped: {exc}"

    expiration_probe = prepare_expiration_probe()
    results["tests"]["replay"] = run_replay_test()
    results["tests"]["concurrency"] = run_concurrency_test()
    results["tests"]["stress"] = run_stress_test()
    results["tests"]["expiration"] = execute_expiration_probe(expiration_probe)
    results["tests"]["multi_instance"] = run_multi_instance_probe()

    replay = results["tests"]["replay"]
    if replay["first_select_status"] != 200 or replay["second_select_status"] == 200:
        add_anomaly(
            results["anomalies"],
            "CRITICAL" if replay["second_select_status"] == 200 else "HIGH",
            "Replay protection failure",
            f"Replay sequence returned {replay['first_select_status']} then {replay['second_select_status']}.",
        )

    concurrency = results["tests"]["concurrency"]
    if concurrency["success_200"] > 1:
        add_anomaly(
            results["anomalies"],
            "CRITICAL",
            "Concurrent double-consumption",
            f"{concurrency['success_200']} parallel requests succeeded for the same login_ticket.",
        )
    elif not concurrency["pass"]:
        add_anomaly(
            results["anomalies"],
            "HIGH",
            "Unexpected concurrency behavior",
            f"Concurrency probe returned success={concurrency['success_200']}, unauthorized={concurrency['unauthorized_401']}, other={concurrency['other_statuses']}.",
        )

    expiration = results["tests"]["expiration"]
    if not expiration["pass"]:
        add_anomaly(
            results["anomalies"],
            "HIGH",
            "Expired ticket accepted",
            f"After waiting {expiration['wait_seconds']} seconds, select-context returned {expiration['select_status_after_expiration']}.",
        )

    stress = results["tests"]["stress"]
    if stress["replay_success_count"] > 0:
        add_anomaly(
            results["anomalies"],
            "CRITICAL",
            "Stress replay breach",
            f"{stress['replay_success_count']} replay attempts succeeded during the {stress['iterations']}-iteration stress run.",
        )
    elif stress["anomalies_count"] > 0:
        add_anomaly(
            results["anomalies"],
            "MEDIUM",
            "Stress anomalies",
            f"{stress['anomalies_count']} unexpected responses were captured during the {stress['iterations']}-iteration stress run.",
        )

    multi_instance = results["tests"]["multi_instance"]
    if multi_instance["executed"] and not multi_instance["pass"]:
        add_anomaly(
            results["anomalies"],
            "CRITICAL",
            "Multi-instance consumption breach",
            f"Primary status={multi_instance['primary_select_status']}, secondary status={multi_instance['secondary_select_status']}.",
        )

    results["verdict"] = build_verdict(results["anomalies"])
    return results


def write_report(results: dict[str, Any]) -> Path:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(render_report(results), encoding="utf-8")
    return REPORT_PATH


def main() -> int:
    results = run_audit()
    report_path = write_report(results)
    print(json.dumps({"report_path": str(report_path), "verdict": results["verdict"], "anomalies": results["anomalies"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
