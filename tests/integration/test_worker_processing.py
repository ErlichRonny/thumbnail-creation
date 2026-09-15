import io
import uuid

from PIL import Image as PILImage
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.constants import ImageStatus
from app.services.repository import get_image_by_id, insert_image
from app.services.storage import save_original
from app.worker import process_one
from tests.conftest import TEST_DATABASE_URL


def _make_jpeg_bytes(width: int = 400, height: int = 200) -> bytes:
    buf = io.BytesIO()
    PILImage.new("RGB", (width, height), color="green").save(buf, format="JPEG")
    return buf.getvalue()


async def test_process_one_resizes_and_marks_done(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    data = _make_jpeg_bytes(400, 200)
    image_id = uuid.uuid4()
    storage_path = save_original(image_id, "image/jpeg", data)

    await insert_image(
        db_session,
        id=image_id,
        original_file_name="cat.jpg",
        original_storage_path=storage_path,
        original_width=400,
        original_height=200,
        content_type="image/jpeg",
        file_size_bytes=len(data),
        preset="small",
    )

    test_engine = create_async_engine(TEST_DATABASE_URL)
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    got_job = await process_one(test_session_factory)
    assert got_job is True

    async with test_session_factory() as verify_session:
        updated = await get_image_by_id(verify_session, image_id)
        assert updated.status == ImageStatus.DONE
        assert updated.thumbnail_width == 150
        assert updated.thumbnail_height == 75
        assert updated.thumbnail_storage_path is not None

    await test_engine.dispose()


async def test_process_one_marks_failed_on_corrupt_image(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    # Truncate a valid JPEG down to a header-only fragment: it still passes
    # magic-byte sniffing at upload time, but PIL cannot fully decode it.
    truncated = _make_jpeg_bytes(400, 200)[:20]
    image_id = uuid.uuid4()
    storage_path = save_original(image_id, "image/jpeg", truncated)

    await insert_image(
        db_session,
        id=image_id,
        original_file_name="broken.jpg",
        original_storage_path=storage_path,
        original_width=400,
        original_height=200,
        content_type="image/jpeg",
        file_size_bytes=len(truncated),
        preset="small",
    )

    test_engine = create_async_engine(TEST_DATABASE_URL)
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    got_job = await process_one(test_session_factory)
    assert got_job is True

    async with test_session_factory() as verify_session:
        updated = await get_image_by_id(verify_session, image_id)
        assert updated.status == ImageStatus.FAILED
        assert updated.error_message is not None

    await test_engine.dispose()


async def test_process_one_returns_false_when_no_pending_jobs(db_session):
    test_engine = create_async_engine(TEST_DATABASE_URL)
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    got_job = await process_one(test_session_factory)
    assert got_job is False

    await test_engine.dispose()
