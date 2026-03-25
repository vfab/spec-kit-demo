"""Health check view for the core application."""

from django.db import OperationalError, connection
from django.http import JsonResponse
from django.views import View


class HealthCheckView(View):
    """
    Returns the application's health status.

    GET /health/ → 200 {"status": "ok", "database": "ok"}
    GET /health/ → 503 {"status": "error", "database": "error", "message": "..."}
    """

    def get(self, request):
        try:
            connection.ensure_connection()
        except OperationalError as e:
            # Sanitize: return only the first line of the error message to
            # avoid leaking hostnames, passwords, or internal config details.
            first_line = str(e).splitlines()[0] if str(e) else "database unavailable"
            return JsonResponse(
                {"status": "error", "database": "error", "message": first_line},
                status=503,
            )
        return JsonResponse({"status": "ok", "database": "ok"}, status=200)
