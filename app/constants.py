from enum import Enum


class ImageStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class Preset(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


PRESET_DIMENSIONS: dict[Preset, tuple[int, int]] = {
    Preset.SMALL: (150, 150),
    Preset.MEDIUM: (400, 400),
    Preset.LARGE: (800, 800),
}

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
