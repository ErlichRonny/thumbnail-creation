import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ImageStatus
from app.models import Image


async def insert_image(db: AsyncSession, **fields) -> Image:
    image = Image(**fields)
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


async def get_image_by_id(db: AsyncSession, image_id: uuid.UUID) -> Image | None:
    result = await db.execute(select(Image).where(Image.id == image_id))
    return result.scalar_one_or_none()


async def claim_pending_job(db: AsyncSession) -> Image | None:
    # FOR UPDATE SKIP LOCKED lets multiple worker processes race this query
    # safely: whichever transaction locks the row first wins it, and any
    # other concurrent caller skips straight past the locked row instead of
    # blocking or double-claiming it.
    result = await db.execute(
        select(Image)
        .where(Image.status == ImageStatus.PENDING)
        .order_by(Image.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    image = result.scalar_one_or_none()
    if image is None:
        return None

    # Flip to processing and commit immediately, so the lock is only held for
    # this short claim transaction, not for the entire resize operation.
    image.status = ImageStatus.PROCESSING
    await db.commit()
    await db.refresh(image)
    return image


async def mark_done(
    db: AsyncSession, image: Image, thumbnail_storage_path: str, thumbnail_width: int, thumbnail_height: int
) -> None:
    image.status = ImageStatus.DONE
    image.thumbnail_storage_path = thumbnail_storage_path
    image.thumbnail_width = thumbnail_width
    image.thumbnail_height = thumbnail_height
    await db.commit()


async def mark_failed(db: AsyncSession, image: Image, error_message: str) -> None:
    image.status = ImageStatus.FAILED
    image.error_message = error_message
    await db.commit()


async def get_status_counts(db: AsyncSession) -> dict[ImageStatus, int]:
    result = await db.execute(select(Image.status, func.count()).group_by(Image.status))
    return dict(result.all())


async def get_average_completion_seconds(db: AsyncSession) -> float | None:
    # Measures upload-to-completion time (created_at -> updated_at for done
    # rows), which includes time spent waiting in the queue, not just the
    # worker's actual resize duration - the only breakdown we have data for.
    result = await db.execute(
        select(func.avg(func.extract("epoch", Image.updated_at - Image.created_at))).where(
            Image.status == ImageStatus.DONE
        )
    )
    return result.scalar_one_or_none()
