import io
import uuid

from sqlalchemy import select

from app.constants import ImageStatus
from app.models import Image
from app.services.repository import insert_image
from app.services.storage import save_thumbnail


def _make_valid_jpeg_bytes() -> bytes:
    from PIL import Image as PILImage

    buf = io.BytesIO()
    PILImage.new("RGB", (200, 100), color="red").save(buf, format="JPEG")
    return buf.getvalue()


async def test_upload_valid_image_returns_202_and_creates_pending_row(client, db_session):
    data = _make_valid_jpeg_bytes()
    response = await client.post(
        "/images",
        files=[("files", ("cat.jpg", data, "image/jpeg"))],
        data={"preset": "medium"},
    )

    assert response.status_code == 202
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "pending"
    assert body[0]["original_width"] == 200
    assert body[0]["original_height"] == 100
    assert body[0]["preset"] == "medium"
    assert body[0]["file_url"].endswith("/file")

    result = await db_session.execute(select(Image))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].status == ImageStatus.PENDING


async def test_upload_invalid_file_type_returns_400_and_creates_no_row(client, db_session):
    response = await client.post(
        "/images",
        files=[("files", ("fake.jpg", b"not an image", "image/jpeg"))],
        data={"preset": "medium"},
    )

    assert response.status_code == 400

    result = await db_session.execute(select(Image))
    rows = result.scalars().all()
    assert len(rows) == 0


async def test_upload_both_preset_and_custom_dims_returns_400(client):
    data = _make_valid_jpeg_bytes()
    response = await client.post(
        "/images",
        files=[("files", ("cat.jpg", data, "image/jpeg"))],
        data={"preset": "medium", "width": 100, "height": 100},
    )

    assert response.status_code == 400


async def test_upload_multiple_files_creates_multiple_rows(client, db_session):
    data = _make_valid_jpeg_bytes()
    response = await client.post(
        "/images",
        files=[
            ("files", ("one.jpg", data, "image/jpeg")),
            ("files", ("two.jpg", data, "image/jpeg")),
        ],
        data={"preset": "small"},
    )

    assert response.status_code == 202
    assert len(response.json()) == 2

    result = await db_session.execute(select(Image))
    rows = result.scalars().all()
    assert len(rows) == 2


async def test_get_metadata_returns_200_for_existing_image(client, db_session):
    data = _make_valid_jpeg_bytes()
    image = await insert_image(
        db_session,
        original_file_name="cat.jpg",
        original_storage_path="/tmp/cat.jpg",
        original_width=200,
        original_height=100,
        content_type="image/jpeg",
        file_size_bytes=len(data),
        preset="medium",
    )

    response = await client.get(f"/images/{image.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(image.id)
    assert body["status"] == "pending"


async def test_get_metadata_returns_404_for_unknown_id(client):
    response = await client.get(f"/images/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_get_file_returns_thumbnail_bytes_when_done(client, db_session, tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    data = _make_valid_jpeg_bytes()
    image_id = uuid.uuid4()
    thumbnail_path = save_thumbnail(image_id, "image/jpeg", data)

    await insert_image(
        db_session,
        id=image_id,
        original_file_name="cat.jpg",
        original_storage_path="/tmp/cat.jpg",
        thumbnail_storage_path=thumbnail_path,
        thumbnail_width=200,
        thumbnail_height=100,
        original_width=200,
        original_height=100,
        content_type="image/jpeg",
        file_size_bytes=len(data),
        preset="medium",
        status=ImageStatus.DONE,
    )

    response = await client.get(f"/images/{image_id}/file")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == data


async def test_get_file_returns_404_when_pending(client, db_session):
    image = await insert_image(
        db_session,
        original_file_name="cat.jpg",
        original_storage_path="/tmp/cat.jpg",
        original_width=200,
        original_height=100,
        content_type="image/jpeg",
        file_size_bytes=123,
        preset="medium",
    )

    response = await client.get(f"/images/{image.id}/file")

    assert response.status_code == 404


async def test_get_file_returns_404_for_unknown_id(client):
    response = await client.get(f"/images/{uuid.uuid4()}/file")
    assert response.status_code == 404
