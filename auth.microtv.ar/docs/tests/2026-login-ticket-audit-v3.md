# 2026 Login Ticket Audit

## 1. Environment description

- Service URL: `http://127.0.0.1:8001`
- Health endpoint: `GET /health` -> `200`
- Health body: `{"status":"ok"}`
- Database URL: `postgresql://microtv:***@localhost/auth_microtv`
- Login ticket TTL configured by service: `10` minutes
- Host platform: `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39`
- Python runtime used for the audit harness: `3.12.3`
- Audit dataset user: `audit.login.ticket@test.com`

## 2. Test methodology

The audit used a controlled multi-tenant user persisted in PostgreSQL and exercised the production endpoints only:

1. `POST /v1/auth/login`
2. `POST /v1/auth/select-context`

Scenarios executed:

1. Replay: `login -> select-context -> select-context` using the same `login_ticket`
2. Concurrency: `100` parallel `select-context` requests against the same `login_ticket`
3. Expiration: `login -> wait until JWT exp -> select-context`
4. Stress: `1000` full iterations of `login -> select-context -> replay attempt`
5. Optional multi-instance probe when two base URLs are supplied via `AUTH_INSTANCE_URLS`

The dataset was reset through PostgreSQL before execution so the same user and memberships were used across all scenarios.

## 3. Replay results

- Login status: `200`
- First `select-context`: `200`
- Second `select-context` with the same ticket: `401`
- Result: `PASS`

## 4. Concurrency results

- Parallel requests: `100`
- Worker threads: `50`
- Successful `200` responses: `1`
- Unauthorized `401` responses: `99`
- Other statuses: `[]`
- Result: `PASS`

## 5. Expiration results

- Login status: `200`
- Wait time until expiration: `601` seconds
- `select-context` after expiration: `200`
- Result: `FAIL`

## 6. Stress results

- Iterations executed: `1000`
- First `select-context` successes: `1000`
- Replay successes detected: `0`
- Stress anomalies recorded: `0`
- Login latency: avg `66.93` ms, p95 `75.19` ms, max `128.21` ms
- Select-context latency: avg `8.74` ms, p95 `10.21` ms, max `76.32` ms
- Result: `PASS`

## 7. Optional multi-instance simulation

- Not executed: Two auth instance URLs were not provided via AUTH_INSTANCE_URLS.

## 8. Anomalies detected

### A1 - Expired ticket accepted
- Severity: **HIGH**
- Evidence: After waiting 601 seconds, select-context returned 200.

## 9. Final verdict

**Verdict: PARTIAL PASS**

Highest observed severity: HIGH.

Severity summary:

- `CRITICAL`: 0
- `HIGH`: 1
- `MEDIUM`: 0
- `LOW`: 0
