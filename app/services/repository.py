import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
