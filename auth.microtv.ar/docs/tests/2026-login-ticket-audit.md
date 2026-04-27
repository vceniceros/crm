# 2026 Login Ticket Audit — auth.microtv.ar (clean rerun)

## 1) Environment description

- Service URL: `http://localhost:8001`
- Project: `auth.microtv.ar`
- Endpoints tested:
  - `POST /v1/auth/login`
  - `POST /v1/auth/select-context`
- Health endpoint: `GET /health` → `200 {"status":"ok"}`
- Test dataset: dedicated multi-tenant audit user in PostgreSQL.

---

## 2) Test methodology

Executed exactly the requested suite (without modifying production code):

1. Replay test (`login -> select-context -> select-context` with same ticket)
2. Concurrency test (100 parallel `select-context` requests with same ticket)
3. Expiration test (login, wait ticket expiration, then `select-context`)
4. Stress test (1000 iterations of `login -> select-context`, plus replay check)
5. Optional multi-instance simulation: not executed (single instance available in this environment)

---

## 3) Replay results

Observed:
- `login`: `200`
- first `select-context`: `200`
- second `select-context` with same ticket: `401`

Expected:
- first request success
- second request `401`

Result: ✅ **PASS**

---

## 4) Concurrency results

Test: 100 parallel requests to `POST /v1/auth/select-context` using the same `login_ticket`.

Observed:
- `200`: **1**
- `401`: **99**
- other statuses: **0**

Expected:
- exactly one success
- all others `401`

Result: ✅ **PASS**

---

## 5) Expiration results

Test:
- login (ticket issued)
- wait until token `exp` + 1s (observed wait: 601s)
- call `select-context`

Observed:
- `select-context` after expiration: `401`

Expected:
- `401`

Result: ✅ **PASS**

---

## 6) Stress results

Iterations executed: **1000** (minimum met)

Observed:
- first select success: **1000/1000**
- replay success count: **0**
- anomalies: **0**

Latency:
- login avg: **72.44 ms** (p95: 85.33 ms, max: 505.74 ms)
- select avg: **27.89 ms** (p95: 82.6 ms, max: 7127.24 ms)

Result: ✅ **PASS**

---

## 7) Anomalies detected

- No double-consumption detected.
- No replay bypass detected.
- No race condition detected in tested scenarios.
- Latency spikes were observed in select max latency (`7127 ms`) but without correctness impact.

---

## 8) Final verdict

**Verdict: PASS** for production safety of login_ticket flow in this test run.

The tested implementation behaved correctly for:
- one-time atomic consumption,
- replay resistance,
- concurrent contention (single winner),
- expiration enforcement,
- high-iteration stability.

Severity summary:
- **CRITICAL:** 0
- **HIGH:** 0
- **MEDIUM:** 0
- **LOW:** 0
