from fastapi import APIRouter, Depends
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.constants import ImageStatus
from app.db import get_db
from app.metrics import (
    IMAGE_AVG_COMPLETION_SECONDS,
    IMAGES_BY_STATUS,
    IMAGES_PROCESSED_TOTAL,
)
from app.services.repository import get_average_completion_seconds, get_status_counts

router = APIRouter()


@router.get("/metrics")
async def metrics(db: AsyncSession = Depends(get_db)):
    counts = await get_status_counts(db)
    for status in ImageStatus:
        IMAGES_BY_STATUS.labels(status=status.value).set(counts.get(status, 0))

    processed_total = counts.get(ImageStatus.DONE, 0) + counts.get(ImageStatus.FAILED, 0)
    IMAGES_PROCESSED_TOTAL.set(processed_total)

    avg_seconds = await get_average_completion_seconds(db)
    IMAGE_AVG_COMPLETION_SECONDS.set(avg_seconds or 0)

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
