import pytest

from app.services.validation import (
    ValidationError,
    sniff_content_type,
    validate_file_count,
    validate_resize_spec,
    validate_upload_file,
)

JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 20
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
WEBP_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 20
GARBAGE_BYTES = b"not an image" * 5


def test_sniff_content_type_recognizes_jpeg():
    assert sniff_content_type(JPEG_BYTES) == "image/jpeg"


def test_sniff_content_type_recognizes_png():
    assert sniff_content_type(PNG_BYTES) == "image/png"


def test_sniff_content_type_recognizes_webp():
    assert sniff_content_type(WEBP_BYTES) == "image/webp"


def test_sniff_content_type_returns_none_for_garbage():
    assert sniff_content_type(GARBAGE_BYTES) is None


def test_validate_upload_file_accepts_valid_jpeg():
    assert validate_upload_file("cat.jpg", JPEG_BYTES) == "image/jpeg"


def test_validate_upload_file_rejects_empty_file():
    with pytest.raises(ValidationError):
        validate_upload_file("empty.jpg", b"")


def test_validate_upload_file_rejects_oversized_file():
    with pytest.raises(ValidationError):
        validate_upload_file("huge.jpg", JPEG_BYTES + b"\x00" * (10 * 1024 * 1024))


def test_validate_upload_file_rejects_spoofed_extension():
    # .jpg filename, but bytes are not a recognized image format
    with pytest.raises(ValidationError):
        validate_upload_file("fake.jpg", GARBAGE_BYTES)


def test_validate_file_count_rejects_zero_files():
    with pytest.raises(ValidationError):
        validate_file_count(0)


def test_validate_file_count_rejects_too_many_files():
    with pytest.raises(ValidationError):
        validate_file_count(21)


def test_validate_file_count_accepts_within_limit():
    validate_file_count(5)


def test_validate_resize_spec_accepts_preset_only():
    spec = validate_resize_spec(preset="medium", width=None, height=None)
    assert spec.preset.value == "medium"
    assert spec.width is None


def test_validate_resize_spec_accepts_custom_dimensions_only():
    spec = validate_resize_spec(preset=None, width=200, height=100)
    assert spec.preset is None
    assert spec.width == 200
    assert spec.height == 100


def test_validate_resize_spec_rejects_both_preset_and_custom():
    with pytest.raises(ValidationError):
        validate_resize_spec(preset="medium", width=200, height=100)


def test_validate_resize_spec_rejects_neither():
    with pytest.raises(ValidationError):
        validate_resize_spec(preset=None, width=None, height=None)


def test_validate_resize_spec_rejects_unknown_preset():
    with pytest.raises(ValidationError):
        validate_resize_spec(preset="huge", width=None, height=None)


def test_validate_resize_spec_rejects_zero_dimension():
    with pytest.raises(ValidationError):
        validate_resize_spec(preset=None, width=0, height=100)


def test_validate_resize_spec_rejects_negative_dimension():
    with pytest.raises(ValidationError):
        validate_resize_spec(preset=None, width=-5, height=100)


def test_validate_resize_spec_rejects_dimension_over_max():
    with pytest.raises(ValidationError):
        validate_resize_spec(preset=None, width=5000, height=100)
