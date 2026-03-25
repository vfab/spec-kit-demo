"""
Production settings for ShopHub.

Inherits all base settings and overrides/adds production-only configuration:
- Reads SECRET_KEY, DATABASE_URL, ALLOWED_HOSTS from environment
- Enforces HTTPS-related security settings
- Configures WhiteNoise for static file serving
- Configures structured JSON logging to stdout
"""

from .settings import *  # noqa: F401, F403

from decouple import Csv, config

# ---------------------------------------------------------------------------
# Core security overrides
# ---------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY")
DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())

# ---------------------------------------------------------------------------
# Database — must be supplied via DATABASE_URL in production
# ---------------------------------------------------------------------------
import dj_database_url  # noqa: E402

DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ---------------------------------------------------------------------------
# HTTPS / Security headers
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ---------------------------------------------------------------------------
# WhiteNoise — static file serving without a CDN
# Insert immediately after SecurityMiddleware (index 1)
# ---------------------------------------------------------------------------
# Build the final MIDDLEWARE list: insert whitenoise after SecurityMiddleware
_middleware = list(MIDDLEWARE)  # type: ignore[name-defined]
_security_idx = next(
    i
    for i, m in enumerate(_middleware)
    if m == "django.middleware.security.SecurityMiddleware"
)
_middleware.insert(_security_idx + 1, "whitenoise.middleware.WhiteNoiseMiddleware")
MIDDLEWARE = _middleware

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_MAX_AGE = 31536000

# ---------------------------------------------------------------------------
# Structured JSON logging — all output goes to stdout for log aggregation
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(timestamp)s %(level)s %(name)s %(message)s",
            "rename_fields": {"levelname": "level", "asctime": "timestamp"},
        },
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "handlers": ["stdout"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["stdout"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["stdout"],
            "level": "ERROR",
            "propagate": False,
        },
        "ecommerce_site": {
            "handlers": ["stdout"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
