"""
Tests for the /health/ endpoint (T-005, EPIC-11).

Covers:
- 200 response when database and cache are healthy
- 503 response when database raises OperationalError
- 200 "degraded" response when only the cache is down
- Message sanitization (no internal details leaked)
- No authentication required (public endpoint)
- Cache status field always present in response
"""

from unittest.mock import patch

import pytest

from django.db import OperationalError
from django.test import Client


@pytest.mark.django_db
class TestHealthCheck:
    def setup_method(self):
        self.client = Client()

    def test_health_check_healthy(self):
        """GET /health/ returns 200 with status ok when DB and cache are up."""
        with patch("django.db.connection.ensure_connection"):
            response = self.client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"
        assert data["cache"] == "ok"

    def test_health_check_db_error(self):
        """GET /health/ returns 503 when DB raises OperationalError."""
        with patch(
            "django.db.connection.ensure_connection",
            side_effect=OperationalError("connection refused"),
        ):
            response = self.client.get("/health/")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "error"
        assert data["database"] == "error"

    def test_health_message_does_not_leak_internals(self):
        """Message field contains only the first line; no hostname leakage."""
        with patch(
            "django.db.connection.ensure_connection",
            side_effect=OperationalError("line1\nline2\nhostname=secret"),
        ):
            response = self.client.get("/health/")
        assert response.status_code == 503
        data = response.json()
        # Must not contain newlines
        assert "\n" not in data["message"]
        # Must not leak the hostname line
        assert "hostname" not in data["message"]
        # Must contain only the first line
        assert data["message"] == "line1"

    def test_health_url_requires_no_auth(self):
        """GET /health/ as AnonymousUser returns 200, not 302."""
        with patch("django.db.connection.ensure_connection"):
            response = self.client.get("/health/")
        # Must not redirect to login
        assert response.status_code != 302
        assert response.status_code == 200

    def test_health_check_includes_cache_field(self):
        """Response always contains a 'cache' field."""
        with patch("django.db.connection.ensure_connection"):
            response = self.client.get("/health/")
        assert "cache" in response.json()

    def test_health_check_degraded_when_cache_set_fails(self):
        """GET /health/ returns 200 degraded when cache.set raises."""
        with patch("django.db.connection.ensure_connection"):
            with patch(
                "django.core.cache.cache.set",
                side_effect=Exception("Redis unavailable"),
            ):
                response = self.client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "ok"
        assert data["cache"] == "error"
        assert data["status"] == "degraded"

    def test_health_check_degraded_when_cache_get_mismatch(self):
        """GET /health/ returns degraded when cache round-trip fails silently."""
        with patch("django.db.connection.ensure_connection"):
            with patch("django.core.cache.cache.get", return_value=None):
                response = self.client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["cache"] == "error"
        assert data["status"] == "degraded"
