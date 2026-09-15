from dataclasses import dataclass

from app.config import settings
from app.constants import ALLOWED_CONTENT_TYPES, Preset

_MAGIC_SIGNATURES: dict[str, bytes] = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
}


class ValidationError(Exception):
    pass


@dataclass
class ResizeSpec:
    preset: Preset | None
    width: int | None
    height: int | None


def sniff_content_type(data: bytes) -> str | None:
    # Check actual file bytes against known magic-number signatures, rather than
    # trusting the client-supplied filename/Content-Type header, which is easy to spoof.
    for content_type, signature in _MAGIC_SIGNATURES.items():
        if data.startswith(signature):
            return content_type
    # WEBP's signature isn't a simple prefix: it's a RIFF container with "WEBP"
    # starting at byte 8, following a 4-byte little-endian chunk size at bytes 4-7.
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_file_count(num_files: int) -> None:
    # Reject a request with no files, and cap the batch size to bound how much
    # work a single POST can enqueue.
    if num_files == 0:
        raise ValidationError("At least one file is required")
    if num_files > settings.max_files_per_request:
        raise ValidationError(f"Too many files: max {settings.max_files_per_request} per request")


def validate_upload_file(filename: str, data: bytes) -> str:
    # Reject zero-byte uploads before doing any further work on them.
    if len(data) == 0:
        raise ValidationError(f"{filename}: file is empty")
    # Bound file size up front so we don't buffer/store arbitrarily large uploads.
    if len(data) > settings.max_file_size_bytes:
        raise ValidationError(f"{filename}: file exceeds max size of {settings.max_file_size_bytes} bytes")

    # The sniffed type (not the client's declared one) becomes the source of truth
    # for what gets stored and processed.
    content_type = sniff_content_type(data)
    if content_type is None or content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(f"{filename}: unsupported or unrecognized image format")

    return content_type


def validate_resize_spec(preset: str | None, width: int | None, height: int | None) -> ResizeSpec:
    has_preset = preset is not None
    has_custom = width is not None or height is not None

    # Exactly one of preset or custom dimensions must be supplied, never both or neither.
    if has_preset and has_custom:
        raise ValidationError("Provide either a preset or custom dimensions, not both")
    if not has_preset and not has_custom:
        raise ValidationError("Provide either a preset or custom dimensions")

    if has_preset:
        # Must be one of the known preset names, not an arbitrary string.
        try:
            preset_enum = Preset(preset)
        except ValueError:
            raise ValidationError(f"Unknown preset: {preset}")
        return ResizeSpec(preset=preset_enum, width=None, height=None)

    if width is None or height is None:
        raise ValidationError("Custom dimensions require both width and height")

    # Custom dimensions must be positive and within sane bounds, so a request can't
    # ask for a 1x1 or a 50000x50000 thumbnail.
    for label, value in (("width", width), ("height", height)):
        if not (settings.min_custom_dimension <= value <= settings.max_custom_dimension):
            raise ValidationError(
                f"Custom {label} must be between {settings.min_custom_dimension} "
                f"and {settings.max_custom_dimension}"
            )

    return ResizeSpec(preset=None, width=width, height=height)
