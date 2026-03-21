"""Custom logging filters for ecommerce_site (EPIC-11 T2)."""

import logging


class SlowQueryFilter(logging.Filter):
    """Suppress SQL log records whose execution time is below the threshold.

    django.db.backends emits a ``LogRecord`` with a ``duration`` attribute
    (milliseconds, float) for every SQL statement when ``DEBUG=True``.
    This filter keeps only records that meet or exceed *threshold_ms* so the
    console is not flooded with fast queries.

    Configure via LOGGING in settings.py::

        "filters": {
            "slow_query": {
                "()" : "ecommerce_site.log_filters.SlowQueryFilter",
                "threshold_ms": 100,
            }
        }
    """

    def __init__(self, name: str = "", threshold_ms: float = 100.0) -> None:
        super().__init__(name)
        self.threshold_ms = threshold_ms

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        duration = getattr(record, "duration", 0.0)
        return float(duration) >= self.threshold_ms
