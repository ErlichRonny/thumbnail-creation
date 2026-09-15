import logging

from fastapi import FastAPI

from app.metrics import REQUESTS_IN, REQUESTS_OUT
from app.routers import health, images, metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Thumbnail Creation API")
app.include_router(health.router)
app.include_router(images.router)
app.include_router(metrics.router)


@app.middleware("http")
async def track_request_counts(request, call_next):
    REQUESTS_IN.labels(method=request.method).inc()
    response = await call_next(request)
    # Use the matched route's path template (e.g. "/images/{image_id}"), not
    # the raw URL, so per-id paths don't blow up label cardinality. Falls back
    # to the raw path for unmatched routes (404s).
    route = request.scope.get("route")
    path = route.path if route is not None else request.url.path
    REQUESTS_OUT.labels(method=request.method, path=path, status_code=response.status_code).inc()
    return response
