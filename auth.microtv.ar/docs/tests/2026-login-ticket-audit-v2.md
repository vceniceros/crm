# 2026 Login Ticket Audit v2 — JWT expiration verification fix

## Scope
Re-run focused on end-to-end natural expiration behavior of `login_ticket`, while re-checking replay/concurrency/stress guarantees.

Service: `http://localhost:8001`

## Required checks

1. **login returns 200**
   - Result: ✅ PASS (`POST /v1/auth/login` => `200`)

2. **replay remains blocked: 200 then 401**
   - Result: ✅ PASS
   - Sequence:
     - first `select-context` with fresh ticket => `200`
     - replay `select-context` with same ticket => `401`

3. **concurrency remains correct: exactly 1 success and the rest 401**
   - Result: ✅ PASS
   - 100 parallel requests with same ticket:
     - `200`: **1**
     - `401`: **99**
     - others: **0**

4. **expiration natural-wait test returns 401 after TTL + safety margin**
   - Result: ✅ PASS
   - Method:
     - decode issued JWT `exp`
     - wait until `exp + 1s` (observed wait: **601s**, i.e. TTL + safety margin)
     - call `select-context`
   - Observed status after wait: `401`

5. **stress test still shows 0 replay successes**
   - Result: ✅ PASS
   - 1000 iterations:
     - first select success: **1000/1000**
     - replay successes: **0**

## Expiration-path diagnosis
The expiration test returned `401` after natural wait, so no further isolation branch was required.

- token exp claim generation: no anomaly observed in this run
- decode timing / leeway: no anomaly observed in this run
- wall clock mismatch: no anomaly observed in this run
- test harness timing: no anomaly observed in this run

## Final verdict
**PASS** — the natural expiration path is behaving correctly end-to-end after the JWT expiration verification fix, and replay/concurrency/stress protections remain intact.
