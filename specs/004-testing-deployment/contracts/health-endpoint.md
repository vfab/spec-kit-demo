# Contract: Health Check Endpoint

**Feature**: `004-testing-deployment`
**Endpoint**: `GET /health/`
**Date**: 2026-03-24

## Overview

The `/health/` endpoint is a public liveness and readiness probe consumed by:
- UptimeRobot (polled every 5 minutes) — FR-018
- GitHub Actions `deploy.yml` health-check poll after each deployment
- Docker `HEALTHCHECK` instruction — FR-035
- Platform (Fly.io) health-check configuration — `[[services.http_checks]]` in `fly.toml`

## Endpoint Specification

### Request

```
GET /health/ HTTP/1.1
Host: <application host>
```

No authentication required. No request body. No query parameters.

### Response — Healthy (HTTP 200)

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-store, no-cache

{
  "status": "ok",
  "database": "ok"
}
```

**Condition**: Application process is running and a database connection can be established (verified via `connection.ensure_connection()`).

### Response — Unhealthy (HTTP 503)

```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json
Cache-Control: no-store, no-cache

{
  "status": "error",
  "database": "error",
  "message": "could not connect to server: Connection refused"
}
```

**Condition**: Any of the following:
- Database connection fails (`OperationalError`)
- Database query times out (> 5 seconds)

**Message field rules**:
- Present only when `status == "error"`
- Contains only the first line of the exception message (`str(exc).split("\n")[0]`)
- MUST NOT contain: hostnames, port numbers, credentials, IP addresses, internal error codes, or stack traces

## Constraints

| Constraint | Value | Source |
|------------|-------|--------|
| Maximum response time | 500 ms | SC-006 |
| Response time in failure mode | < 10 seconds | SC-006 |
| Authentication required | No | FR-017 |
| Rate limiting applied | No | FR-018 (monitoring must not be blocked) |
| HTTP methods accepted | GET only | — |
| Caching | `Cache-Control: no-store` | Responses must reflect live state |

## URL Registration

```python
# ecommerce_site/urls.py
urlpatterns = [
    path("", include("core.urls")),  # Must be first — before products/accounts/orders
    path("admin/", admin.site.urls),
    path("", include("products.urls")),
    ...
]

# core/urls.py
from django.urls import path
from .views import HealthCheckView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
]
```

## Test Requirements

The following tests MUST exist in `tests/test_health.py`:

| Test | Assertion |
|------|-----------|
| `test_health_returns_200_when_db_healthy` | Mock `connection.ensure_connection` → no-op; GET `/health/` → 200; body `{"status": "ok", "database": "ok"}` |
| `test_health_returns_503_when_db_unreachable` | Mock `connection.ensure_connection` → raises `OperationalError("Connection refused")`; GET `/health/` → 503; body `status == "error"` |
| `test_health_message_does_not_leak_internals` | Confirm `message` field in 503 response is the first line only and contains no newlines |
| `test_health_url_requires_no_auth` | GET `/health/` as anonymous client → no redirect to login |

## Security Notes

- The endpoint is intentionally public (no authentication). It reveals only binary health status — not application version, dependency details, or configuration.
- `Cache-Control: no-store` prevents stale health responses from being served by intermediate proxies.
- The `message` field sanitization (first line of exception only) prevents internal infrastructure details from leaking through the error response.
