from prometheus_client import REGISTRY

from app.constants import ImageStatus
from app.services.repository import insert_image


def _sample_value(name: str, labels: dict | None = None) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


async def test_metrics_reports_status_counts_and_processed_total(client, db_session):
    await insert_image(
        db_session,
        original_file_name="a.jpg",
        original_storage_path="/tmp/a.jpg",
        original_width=100,
        original_height=100,
        content_type="image/jpeg",
        file_size_bytes=1,
        preset="small",
        status=ImageStatus.DONE,
    )
    await insert_image(
        db_session,
        original_file_name="b.jpg",
        original_storage_path="/tmp/b.jpg",
        original_width=100,
        original_height=100,
        content_type="image/jpeg",
        file_size_bytes=1,
        preset="small",
        status=ImageStatus.FAILED,
    )
    await insert_image(
        db_session,
        original_file_name="c.jpg",
        original_storage_path="/tmp/c.jpg",
        original_width=100,
        original_height=100,
        content_type="image/jpeg",
        file_size_bytes=1,
        preset="small",
    )

    response = await client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    assert _sample_value("images_by_status", {"status": "done"}) == 1.0
    assert _sample_value("images_by_status", {"status": "failed"}) == 1.0
    assert _sample_value("images_by_status", {"status": "pending"}) == 1.0
    assert _sample_value("images_by_status", {"status": "processing"}) == 0.0
    assert _sample_value("images_processed_total") == 2.0


async def test_metrics_tracks_request_counters_labeled_by_method_path_and_status(client):
    before_in = _sample_value("http_requests_received_total", {"method": "GET"})
    before_out = _sample_value(
        "http_responses_sent_total", {"method": "GET", "path": "/health", "status_code": "200"}
    )

    await client.get("/health")

    after_in = _sample_value("http_requests_received_total", {"method": "GET"})
    after_out = _sample_value(
        "http_responses_sent_total", {"method": "GET", "path": "/health", "status_code": "200"}
    )

    assert after_in == before_in + 1
    assert after_out == before_out + 1
