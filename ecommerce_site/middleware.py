"""Performance monitoring middleware for ecommerce_site (EPIC-11 T5)."""

import logging
import time

from django.conf import settings

logger = logging.getLogger("ecommerce_site.performance")


class RequestTimingMiddleware:
    """Log the wall-clock duration of every HTTP request.

    Emits one INFO record per request containing:

    ``method``      HTTP verb (GET, POST, …)
    ``path``        URL path (no query string, so no PII in logs)
    ``status_code`` HTTP response status
    ``duration_ms`` Elapsed time in milliseconds, rounded to 2 dp

    In DEBUG mode the ``X-Request-Duration`` response header is also set
    (e.g. ``"47.32ms"``) so developers can inspect timing in browser
    DevTools or the debug toolbar without needing an external APM.

    Add to settings.MIDDLEWARE — ideally early in the stack so the
    measurement spans as much of the request lifecycle as possible::

        "ecommerce_site.middleware.RequestTimingMiddleware",
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        if settings.DEBUG:
            response["X-Request-Duration"] = f"{duration_ms}ms"

        return response
