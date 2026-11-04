import threading
from collections import defaultdict

_lock = threading.Lock()
_counters: defaultdict[str, int] = defaultdict(int)


def increment(name: str, value: int = 1) -> None:
    if not name.replace("_", "").replace(".", "").isalnum():
        raise ValueError("invalid_metric_name")
    with _lock:
        _counters[name] += value


def render_metrics() -> str:
    with _lock:
        lines = ["# TYPE ailiss_requests_total counter"]
        for name in sorted(_counters):
            lines.append(f"ailiss_{name} {_counters[name]}")
        return "\n".join(lines) + "\n"
