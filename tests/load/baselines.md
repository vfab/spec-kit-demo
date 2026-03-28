# Performance Baselines

Performance targets for ShopHub endpoints per spec FR-011.
Measured on first staging run and updated here.

## Baseline Table

| Endpoint | p50 (ms) | p95 (ms) | p99 (ms) | Error Rate |
|---|---|---|---|---|
| `GET /` | TBD — measure on first staging run | TBD — measure on first staging run | TBD — measure on first staging run | TBD |
| `GET /products/` | TBD — measure on first staging run | TBD — measure on first staging run | TBD — measure on first staging run | TBD |
| `GET /products/<slug>/` | TBD — measure on first staging run | TBD — measure on first staging run | TBD — measure on first staging run | TBD |
| `POST /orders/cart/add/` | TBD — measure on first staging run | TBD — measure on first staging run | TBD — measure on first staging run | TBD |
| `GET /orders/cart/` | TBD — measure on first staging run | TBD — measure on first staging run | TBD — measure on first staging run | TBD |

## Thresholds (FR-011, SC-009)

| Metric | Target |
|---|---|
| Homepage p95 | < 1000 ms |
| Any endpoint error rate | < 1% |

## How to Measure

Run the load test against staging (50 users, 60 seconds):

```bash
locust -f tests/load/locustfile.py \
  --host=https://shophub-staging.fly.dev \
  --users=50 \
  --spawn-rate=5 \
  --run-time=60s \
  --headless \
  --html=docs/load-test-report.html
```

Open `docs/load-test-report.html` and record the p50/p95/p99 values for each
endpoint into the table above.

## Notes

- Baseline values must be committed after the first successful staging run.
- p95 for homepage must remain < 1000 ms; any regression should trigger
  a performance review before merging.
- Error rate < 1% is a hard requirement per FR-011.
- The production guard in `locustfile.py` prevents accidental targeting of
  production. To run against staging, `staging` substring must be in the host
  or `LOCUST_ALLOWED_HOSTS` must be set.
