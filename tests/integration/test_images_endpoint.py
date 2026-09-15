import io

from sqlalchemy import select

from app.constants import ImageStatus
from app.models import Image


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
