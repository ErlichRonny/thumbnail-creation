from prometheus_client import Counter, Gauge

# Labeled by method only: the route template isn't known yet when a request
# first arrives, before routing has resolved it.
REQUESTS_IN = Counter("http_requests_received", "Total HTTP requests received", ["method"])
# Labeled by method, route template (not raw path, to avoid per-id cardinality
# blowup on paths like /images/{id}), and status code, once the response is known.
REQUESTS_OUT = Counter("http_responses_sent", "Total HTTP responses sent", ["method", "path", "status_code"])

IMAGES_BY_STATUS = Gauge("images_by_status", "Current number of images in each status", ["status"])
IMAGES_PROCESSED_TOTAL = Gauge("images_processed_total", "Total images the worker has finished (done or failed)")
IMAGE_AVG_COMPLETION_SECONDS = Gauge(
    "image_avg_completion_seconds",
    "Average seconds from upload to completion for images with status=done",
)
