import uuid
from pathlib import Path

from app.config import settings

_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _save(subdir: str, image_id: uuid.UUID, content_type: str, data: bytes) -> str:
    directory = Path(settings.storage_dir) / subdir
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{image_id}{_EXTENSIONS[content_type]}"
    path.write_bytes(data)
    return str(path)


def save_original(image_id: uuid.UUID, content_type: str, data: bytes) -> str:
    return _save("originals", image_id, content_type, data)


def save_thumbnail(image_id: uuid.UUID, content_type: str, data: bytes) -> str:
    return _save("thumbnails", image_id, content_type, data)


def load_original(path: str) -> bytes:
    return Path(path).read_bytes()
