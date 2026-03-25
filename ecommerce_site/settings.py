"""
Django settings for ecommerce_site project.

All environment-specific values are read from environment variables (or a
``.env`` file via python-decouple).  Copy ``.env.example`` to ``.env`` and
adjust the values for your environment.

For the full list of Django settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path

import dj_database_url
from decouple import Csv, config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# No default — a missing SECRET_KEY must fail loudly,
# never silently use an insecure fallback.
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local apps
    "core",
    "accounts",
    "products",
    "orders",
    # Account lockout (EPIC-10 T3)
    "axes",
]

# Developer tooling — only active when DEBUG=True
if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    MIDDLEWARE.insert(1, "debug_toolbar.middleware.DebugToolbarMiddleware")

# axes middleware must come after AxesMiddleware — append after session/auth middleware
MIDDLEWARE.append("axes.middleware.AxesMiddleware")

# IPs that can see the Debug Toolbar panel
INTERNAL_IPS = ["127.0.0.1", "::1"]

# django-axes requires its own backend alongside ModelBackend
AUTHENTICATION_BACKENDS = [
    # AxesStandaloneBackend must be the first backend.
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "ecommerce_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.csrf",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "ecommerce_site.context_processors.global_context",
            ],
        },
    },
]

WSGI_APPLICATION = "ecommerce_site.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
#
# Set DATABASE_URL in your .env to switch backends:
#   SQLite  (default/dev):  sqlite:///db.sqlite3
#   Postgres (production):  postgres://user:pass@host:5432/dbname
_default_db_url = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL", default=_default_db_url),
        conn_max_age=config("DB_CONN_MAX_AGE", default=0, cast=int),
        conn_health_checks=True,
    )
}


# -----------------------------------------------------------------
# Cache (EPIC-11 T3)
# In production set REDIS_URL in .env (e.g. redis://localhost:6379/1).
# Falls back to LocMemCache (in-process) when REDIS_URL is not set so
# the app works out-of-the-box without a Redis server.
# -----------------------------------------------------------------
_redis_url = config("REDIS_URL", default="")
if _redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _redis_url,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                # Gracefully degrade when Redis is unavailable.
                "IGNORE_EXCEPTIONS": True,
            },
            # Global default for cache.set() calls that omit timeout=.
            # Views pass explicit per-key timeouts (CACHE_TIMEOUT_* below)
            # so this value only applies to any future cache.set() without timeout.
            "TIMEOUT": config("CACHE_TIMEOUT", default=300, cast=int),  # 5 min
            "KEY_PREFIX": "ecom",
        }
    }
else:
    # Development / CI fallback — no Redis required.
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

# Cache timeout constants (seconds) for use in views.
CACHE_TIMEOUT_PRODUCT_LIST = config(
    "CACHE_TIMEOUT_PRODUCT_LIST", default=300, cast=int
)  # 5 min
CACHE_TIMEOUT_PRODUCT_DETAIL = config(
    "CACHE_TIMEOUT_PRODUCT_DETAIL", default=600, cast=int
)  # 10 min
CACHE_TIMEOUT_CATEGORY_LIST = config(
    "CACHE_TIMEOUT_CATEGORY_LIST", default=900, cast=int
)  # 15 min


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        # Custom: at least one symbol character (EPIC-10 T3)
        "NAME": "accounts.validators.SymbolPasswordValidator",
    },
]

# -----------------------------------------------------------------
# Password reset (S4)
# Token expires after 1 hour (3600 s).  Django default is 3 days.
# -----------------------------------------------------------------
PASSWORD_RESET_TIMEOUT = config("PASSWORD_RESET_TIMEOUT", default=3600, cast=int)


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Media files (user uploads)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentication URLs (L9)
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# -----------------------------------------------------------------
# Business logic settings (M1)
# -----------------------------------------------------------------
# Tax rate applied at checkout (fraction, e.g. 0.08 = 8 %).
# Override per environment via .env: TAX_RATE=0.10
TAX_RATE = config("TAX_RATE", default=0.08, cast=float)

# Maximum allowed image upload size in megabytes (M2).
# Override per environment via .env: MAX_IMAGE_UPLOAD_MB=10
MAX_IMAGE_UPLOAD_MB = config("MAX_IMAGE_UPLOAD_MB", default=5, cast=int)

# Stock threshold for "low stock" badge on product listings.
# Override per environment via .env: LOW_STOCK_THRESHOLD=10
LOW_STOCK_THRESHOLD = config("LOW_STOCK_THRESHOLD", default=5, cast=int)

# -----------------------------------------------------------------
# Feature flags (F1)
# Toggle incomplete or environment-specific features without a code deploy.
# Set any of these to True in .env to enable the feature in that environment.
# -----------------------------------------------------------------
FEATURE_FLAGS: dict[str, bool] = {
    # Product review system (not yet built — reserved for future sprint)
    "REVIEWS": config("FEATURE_REVIEWS", default=False, cast=bool),
    # Wishlist / saved-items functionality
    "WISHLIST": config("FEATURE_WISHLIST", default=False, cast=bool),
    # Promotional discount code support at checkout
    "DISCOUNT_CODES": config("FEATURE_DISCOUNT_CODES", default=False, cast=bool),
}

# -----------------------------------------------------------------
# Session security (S5)
# -----------------------------------------------------------------
# Sessions expire after 2 hours of inactivity.
SESSION_COOKIE_AGE = config("SESSION_COOKIE_AGE", default=7200, cast=int)
# Close-browser clears the session cookie (defence-in-depth on shared devices).
SESSION_EXPIRE_AT_BROWSER_CLOSE = config(
    "SESSION_EXPIRE_AT_BROWSER_CLOSE", default=False, cast=bool
)
# Prevent JavaScript from reading the session cookie.
SESSION_COOKIE_HTTPONLY = True

# -----------------------------------------------------------------
# Account lockout — django-axes (S6, EPIC-10 T3)
# -----------------------------------------------------------------
# Set AXES_ENABLED=False in .env to disable during testing/development.
AXES_ENABLED = config("AXES_ENABLED", default=True, cast=bool)
AXES_FAILURE_LIMIT = config("AXES_FAILURE_LIMIT", default=5, cast=int)
# Lock duration: 30 minutes.
AXES_COOLOFF_TIME = config("AXES_COOLOFF_TIME", default=0.5, cast=float)  # hours
# Lock by username+IP combo (not IP alone) to reduce false positives.
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]
# Redirect instead of raising a 403 on lockout.
AXES_LOCKOUT_URL = "/accounts/login/?locked=1"
# Reset failures on successful login.
AXES_RESET_ON_SUCCESS = True

# -----------------------------------------------------------------
# Security settings (S1, S2, S3)
# These are safe defaults that tighten up production.
# They are no-ops in local development (DEBUG=True / non-HTTPS).
# -----------------------------------------------------------------
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=False, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=False, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False, cast=bool
)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)

# Prevent browsers from MIME-sniffing a response away from the declared content-type.
SECURE_CONTENT_TYPE_NOSNIFF = True
# Legacy XSS auditor header — harmless no-op in modern browsers (kept for old clients).
SECURE_BROWSER_XSS_FILTER = True
# Block iframe embedding — clickjacking protection (Django 5.2 default; explicit).
X_FRAME_OPTIONS = "DENY"
# Restrict referrer info on cross-origin navigation (privacy + security).
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
# Forward upstream scheme so SECURE_SSL_REDIRECT works behind a proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# -----------------------------------------------------------------
# Content Security Policy (EPIC-10 T5, T12)
# CSPMiddleware adds Content-Security-Policy headers to every response,
# restricting which resources the browser may load.
# Templates contain inline <script> and style= attributes so 'unsafe-inline' is
# added as an incremental first step; nonce-based inline approval is a follow-up.
# -----------------------------------------------------------------
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net")
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
    "https://cdn.jsdelivr.net",
    "https://cdnjs.cloudflare.com",
)
CSP_FONT_SRC = ("'self'", "https://cdnjs.cloudflare.com")
CSP_IMG_SRC = ("'self'", "data:", "blob:")
CSP_CONNECT_SRC = ("'self'",)
# Disallow framing from any origin (mirrors X_FRAME_OPTIONS = DENY).
CSP_FRAME_ANCESTORS = ("'none'",)

# -----------------------------------------------------------------
# Query logging (EPIC-11 T2)
# Logs any SQL query that takes longer than DB_SLOW_QUERY_MS ms when DEBUG=True.
# In production leave DEBUG=False — the django.db.backends logger is silent.
# -----------------------------------------------------------------
DB_SLOW_QUERY_MS = config("DB_SLOW_QUERY_MS", default=100, cast=int)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "slow_query": {
            "()": "ecommerce_site.log_filters.SlowQueryFilter",
            "threshold_ms": DB_SLOW_QUERY_MS,
        },
    },
    "formatters": {
        "sql": {
            "format": "[%(asctime)s] %(duration).1fms  %(sql)s",
        },
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "slow_sql_console": {
            "class": "logging.StreamHandler",
            "formatter": "sql",
            "filters": ["require_debug_true", "slow_query"],
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["slow_sql_console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "ecommerce_site": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        # Log failed login attempts and lockout events (EPIC-10 T13).
        "axes": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        # Log Django's built-in security warnings (e.g. SuspiciousOperation).
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
