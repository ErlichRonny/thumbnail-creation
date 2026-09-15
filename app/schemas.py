import uuid
from datetime import datetime

from pydantic import BaseModel

from app.constants import ImageStatus
from app.models import Image


class ImageMetadata(BaseModel):
    id: uuid.UUID
    status: ImageStatus
    original_filename: str
    content_type: str
    original_width: int
    original_height: int
    thumbnail_width: int | None
    thumbnail_height: int | None
    preset: str | None
    custom_width: int | None
    custom_height: int | None
    file_size_bytes: int
    created_at: datetime
    file_url: str

    @classmethod
    def from_image(cls, image: Image) -> "ImageMetadata":
        return cls(
            id=image.id,
            status=image.status,
            original_filename=image.original_file_name,
            content_type=image.content_type,
            original_width=image.original_width,
            original_height=image.original_height,
            thumbnail_width=image.thumbnail_width,
            thumbnail_height=image.thumbnail_height,
            preset=image.preset,
            custom_width=image.custom_width,
            custom_height=image.custom_height,
            file_size_bytes=image.file_size_bytes,
            created_at=image.created_at,
            file_url=f"/images/{image.id}/file",
        )
