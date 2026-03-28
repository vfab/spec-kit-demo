"""Health check view for the core application."""

from django.core.cache import cache
from django.db import OperationalError, connection
from django.http import JsonResponse
from django.views import View


class HealthCheckView(View):
    """
    Returns the application's health status.

    GET /health/ → 200 {"status": "ok", "database": "ok", "cache": "ok"}
    GET /health/ → 503 {"status": "error", "database": "error",
                         "cache": "ok", "message": "…"}
    GET /health/ → 200 {"status": "degraded", "database": "ok",
                         "cache": "error"}
    """

    _PROBE_KEY = "_health_probe"

    def get(self, request):
        # --- Database check --------------------------------------------------
        db_ok = True
        db_message = None
        try:
            connection.ensure_connection()
        except OperationalError as e:
            db_ok = False
            # Sanitize: return only the first line so hostnames / passwords
            # embedded in connection strings cannot be leaked to callers.
            first_line = str(e).splitlines()[0] if str(e) else "database unavailable"
            db_message = first_line

        # --- Cache check -----------------------------------------------------
        cache_ok = True
        try:
            cache.set(self._PROBE_KEY, "1", timeout=5)
            if cache.get(self._PROBE_KEY) != "1":
                cache_ok = False
        except Exception:
            cache_ok = False

        # --- Build response --------------------------------------------------
        if db_ok and cache_ok:
            overall = "ok"
        elif not db_ok:
            overall = "error"
        else:
            overall = "degraded"

        payload = {
            "status": overall,
            "database": "ok" if db_ok else "error",
            "cache": "ok" if cache_ok else "error",
        }
        if db_message:
            payload["message"] = db_message

        http_status = 503 if not db_ok else 200
        return JsonResponse(payload, status=http_status)
