import logging
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image as PILImage
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ImageStatus
from app.db import get_db
from app.schemas import ImageMetadata
from app.services.repository import get_image_by_id, insert_image
from app.services.storage import save_original
from app.services.validation import (
    ValidationError,
    validate_file_count,
    validate_resize_spec,
    validate_upload_file,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/images", status_code=202, response_model=list[ImageMetadata])
async def upload_images(
    files: list[UploadFile] = File(...),
    preset: str | None = Form(None),
    width: int | None = Form(None),
    height: int | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        validate_file_count(len(files))
        resize_spec = validate_resize_spec(preset, width, height)

        # Validate every file up front so a bad file anywhere in the batch fails
        # the whole request before anything is written to disk or the DB.
        validated = []
        for file in files:
            data = await file.read()
            content_type = validate_upload_file(file.filename, data)
            try:
                with PILImage.open(BytesIO(data)) as img:
                    width_px, height_px = img.size
            except Exception:
                raise ValidationError(f"{file.filename}: could not read image dimensions")
            validated.append((file.filename, content_type, data, width_px, height_px))
    except ValidationError as e:
        logger.info("Upload rejected: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

    results = []
    for filename, content_type, data, width_px, height_px in validated:
        image_id = uuid.uuid4()
        storage_path = save_original(image_id, content_type, data)

        image = await insert_image(
            db,
            id=image_id,
            original_file_name=filename,
            original_storage_path=storage_path,
            preset=resize_spec.preset.value if resize_spec.preset else None,
            custom_width=resize_spec.width,
            custom_height=resize_spec.height,
            original_width=width_px,
            original_height=height_px,
            content_type=content_type,
            file_size_bytes=len(data),
        )
        results.append(ImageMetadata.from_image(image))

    return results


@router.get("/images/{image_id}", response_model=ImageMetadata)
async def get_image_metadata(image_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    image = await get_image_by_id(db, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return ImageMetadata.from_image(image)


@router.get("/images/{image_id}/file")
async def get_image_file(image_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    image = await get_image_by_id(db, image_id)
    if image is None or image.status != ImageStatus.DONE:
        raise HTTPException(status_code=404, detail="Thumbnail not available")
    return FileResponse(path=image.thumbnail_storage_path, media_type=image.content_type)
