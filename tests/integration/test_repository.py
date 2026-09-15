import uuid

from app.constants import ImageStatus
from app.services.repository import get_image_by_id, insert_image


async def test_insert_and_get_image_by_id(db_session):
    image = await insert_image(
        db_session,
        original_file_name="cat.jpg",
        original_storage_path="/data/originals/cat.jpg",
        original_width=1920,
        original_height=1080,
        content_type="image/jpeg",
        file_size_bytes=204800,
        preset="medium",
    )

    assert image.id is not None
    assert image.status == ImageStatus.PENDING

    fetched = await get_image_by_id(db_session, image.id)
    assert fetched is not None
    assert fetched.original_file_name == "cat.jpg"
    assert fetched.preset == "medium"


async def test_get_image_by_id_returns_none_when_missing(db_session):
    result = await get_image_by_id(db_session, uuid.uuid4())
    assert result is None
