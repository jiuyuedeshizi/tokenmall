from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from decimal import Decimal
import json
import logging
from threading import Lock
from time import perf_counter

logger = logging.getLogger("app.observability")

_metrics_lock = Lock()
_counters: dict[str, float] = defaultdict(float)
_timings: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0.0, "sum": 0.0})


def _normalize_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    return value


def log_event(event: str, **fields: object) -> None:
    payload = {"event": event, **{key: _normalize_value(value) for key, value in fields.items()}}
    logger.info(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def increment_metric(name: str, value: float = 1.0) -> None:
    with _metrics_lock:
        _counters[name] += value


def observe_metric(name: str, value: float) -> None:
    with _metrics_lock:
        bucket = _timings[name]
        bucket["count"] += 1.0
        bucket["sum"] += value


def metrics_timer(name: str):
    started_at = perf_counter()

    def _finish() -> float:
        duration = perf_counter() - started_at
        observe_metric(name, duration)
        return duration

    return _finish


def export_metrics_text() -> str:
    lines: list[str] = []
    with _metrics_lock:
        for name in sorted(_counters):
            metric_name = name.replace(".", "_")
            lines.append(f"# TYPE {metric_name} counter")
            lines.append(f"{metric_name} {_counters[name]:.6f}")
        for name in sorted(_timings):
            metric_name = name.replace(".", "_")
            lines.append(f"# TYPE {metric_name}_seconds summary")
            lines.append(f"{metric_name}_seconds_count {_timings[name]['count']:.0f}")
            lines.append(f"{metric_name}_seconds_sum {_timings[name]['sum']:.6f}")
    return "\n".join(lines) + ("\n" if lines else "")


def reset_metrics() -> None:
    with _metrics_lock:
        _counters.clear()
        _timings.clear()
