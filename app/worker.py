import asyncio

from app.config import settings
from app.constants import Preset
from app.db import AsyncSessionLocal
from app.models import Image
from app.services.image_processing import compute_thumbnail_dimensions, resize_image
from app.services.repository import claim_pending_job, mark_done, mark_failed
from app.services.storage import read_bytes, save_thumbnail
from app.services.validation import ResizeSpec


def _resize_spec_from_image(image: Image) -> ResizeSpec:
    preset = Preset(image.preset) if image.preset else None
    return ResizeSpec(preset=preset, width=image.custom_width, height=image.custom_height)


async def process_one(session_factory=AsyncSessionLocal) -> bool:
    async with session_factory() as db:
        image = await claim_pending_job(db)
        if image is None:
            return False

        try:
            data = read_bytes(image.original_storage_path)
            resize_spec = _resize_spec_from_image(image)
            thumb_width, thumb_height = compute_thumbnail_dimensions(
                image.original_width, image.original_height, resize_spec
            )
            thumbnail_bytes = resize_image(data, image.content_type, thumb_width, thumb_height)
            thumbnail_path = save_thumbnail(image.id, image.content_type, thumbnail_bytes)
            await mark_done(db, image, thumbnail_path, thumb_width, thumb_height)
        except Exception as e:
            await db.rollback()
            await mark_failed(db, image, str(e))

        return True


async def worker_loop(session_factory=AsyncSessionLocal) -> None:
    while True:
        got_job = await process_one(session_factory)
        if not got_job:
            await asyncio.sleep(settings.worker_poll_interval_seconds)


async def run(concurrency: int) -> None:
    await asyncio.gather(*(worker_loop() for _ in range(concurrency)))


if __name__ == "__main__":
    asyncio.run(run(settings.worker_concurrency))
