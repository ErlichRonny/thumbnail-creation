import asyncio
import io

from PIL import Image as PILImage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.constants import ImageStatus
from app.models import Image
from app.worker import process_one
from tests.conftest import TEST_DATABASE_URL

N_UPLOADS = 20
N_WORKERS = 5


def _make_jpeg_bytes(width: int = 200, height: int = 100) -> bytes:
    buf = io.BytesIO()
    PILImage.new("RGB", (width, height), color="purple").save(buf, format="JPEG")
    return buf.getvalue()


async def _drain_queue(session_factory, worker_count: int) -> None:
    async def worker_slot():
        while await process_one(session_factory):
            pass

    await asyncio.gather(*(worker_slot() for _ in range(worker_count)))


async def test_concurrent_uploads_and_processing_end_to_end(client, db_session):
    data = _make_jpeg_bytes(200, 100)

    async def upload(i: int):
        return await client.post(
            "/images",
            files=[("files", (f"img{i}.jpg", data, "image/jpeg"))],
            data={"preset": "small"},
        )

    responses = await asyncio.gather(*(upload(i) for i in range(N_UPLOADS)))

    assert all(r.status_code == 202 for r in responses)
    ids = [r.json()[0]["id"] for r in responses]
    assert len(set(ids)) == N_UPLOADS, "every upload should get a unique id, none dropped or duplicated"

    result = await db_session.execute(select(Image))
    rows = result.scalars().all()
    assert len(rows) == N_UPLOADS
    assert all(row.status == ImageStatus.PENDING for row in rows)

    # Simulate multiple worker processes racing for the same pool of pending
    # jobs, against the real test database (not mocked).
    test_engine = create_async_engine(TEST_DATABASE_URL)
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    await _drain_queue(test_session_factory, N_WORKERS)

    async with test_session_factory() as verify_session:
        result = await verify_session.execute(select(Image))
        rows = result.scalars().all()

    assert len(rows) == N_UPLOADS
    done_rows = [row for row in rows if row.status == ImageStatus.DONE]
    assert len(done_rows) == N_UPLOADS, "every row should be processed exactly once, none stuck or lost"
    for row in done_rows:
        assert row.thumbnail_width == 150
        assert row.thumbnail_height == 75
        assert row.thumbnail_storage_path is not None

    await test_engine.dispose()

    # Spot check the result is correct through the real HTTP surface too.
    sample_id = ids[0]
    metadata_response = await client.get(f"/images/{sample_id}")
    assert metadata_response.status_code == 200
    assert metadata_response.json()["status"] == "done"

    file_response = await client.get(f"/images/{sample_id}/file")
    assert file_response.status_code == 200
