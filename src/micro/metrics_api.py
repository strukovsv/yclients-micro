from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP Requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["endpoint"]
)

PROCESS_MEMORY = Gauge(
    "process_resident_memory_bytes_all",
    "Resident memory size in bytes",
    multiprocess_mode="livesum",
)

PROCESS_MEMORY2 = Gauge(
    "process_resident_memory_bytes_by_worker",
    "Resident memory per worker",
    ["pid"],
    multiprocess_mode="liveall",
)
