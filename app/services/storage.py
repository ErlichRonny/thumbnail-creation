import uuid
from pathlib import Path

from app.config import settings

_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def save_original(image_id: uuid.UUID, content_type: str, data: bytes) -> str:
    directory = Path(settings.storage_dir) / "originals"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{image_id}{_EXTENSIONS[content_type]}"
    path.write_bytes(data)
    return str(path)
