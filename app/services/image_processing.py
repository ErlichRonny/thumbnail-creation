from io import BytesIO

from PIL import Image as PILImage

from app.constants import PRESET_DIMENSIONS
from app.services.validation import ResizeSpec

_PIL_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


def compute_thumbnail_dimensions(original_width: int, original_height: int, resize_spec: ResizeSpec) -> tuple[int, int]:
    if resize_spec.preset is not None:
        target_width, target_height = PRESET_DIMENSIONS[resize_spec.preset]
    else:
        target_width, target_height = resize_spec.width, resize_spec.height

    # Fit within the target box while preserving aspect ratio; cap the scale
    # factor at 1.0 so small originals are never upscaled into blurry thumbnails.
    scale = min(target_width / original_width, target_height / original_height, 1.0)

    thumbnail_width = max(1, round(original_width * scale))
    thumbnail_height = max(1, round(original_height * scale))
    return thumbnail_width, thumbnail_height


def resize_image(data: bytes, content_type: str, target_width: int, target_height: int) -> bytes:
    with PILImage.open(BytesIO(data)) as img:
        resized = img.resize((target_width, target_height), PILImage.LANCZOS)
        output = BytesIO()
        resized.save(output, format=_PIL_FORMATS[content_type])
        return output.getvalue()
