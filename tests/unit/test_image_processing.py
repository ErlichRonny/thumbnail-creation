import io

from PIL import Image as PILImage

from app.constants import Preset
from app.services.image_processing import compute_thumbnail_dimensions, resize_image
from app.services.validation import ResizeSpec


def _make_jpeg_bytes(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    PILImage.new("RGB", (width, height), color="blue").save(buf, format="JPEG")
    return buf.getvalue()


def test_compute_dimensions_landscape_fits_within_preset_box():
    spec = ResizeSpec(preset=Preset.MEDIUM, width=None, height=None)
    width, height = compute_thumbnail_dimensions(2000, 1000, spec)
    # medium box is 400x400; landscape 2:1 should be limited by width -> 400x200
    assert (width, height) == (400, 200)


def test_compute_dimensions_portrait_fits_within_preset_box():
    spec = ResizeSpec(preset=Preset.MEDIUM, width=None, height=None)
    width, height = compute_thumbnail_dimensions(1000, 2000, spec)
    # limited by height -> 200x400
    assert (width, height) == (200, 400)


def test_compute_dimensions_square_fits_within_preset_box():
    spec = ResizeSpec(preset=Preset.SMALL, width=None, height=None)
    width, height = compute_thumbnail_dimensions(1000, 1000, spec)
    assert (width, height) == (150, 150)


def test_compute_dimensions_does_not_upscale_small_images():
    spec = ResizeSpec(preset=Preset.LARGE, width=None, height=None)
    width, height = compute_thumbnail_dimensions(50, 50, spec)
    assert (width, height) == (50, 50)


def test_compute_dimensions_custom_target():
    spec = ResizeSpec(preset=None, width=300, height=300)
    width, height = compute_thumbnail_dimensions(600, 300, spec)
    # 2:1 image fit into 300x300 -> limited by width -> 300x150
    assert (width, height) == (300, 150)


def test_resize_image_produces_expected_pixel_dimensions():
    data = _make_jpeg_bytes(2000, 1000)
    resized_bytes = resize_image(data, "image/jpeg", 400, 200)

    with PILImage.open(io.BytesIO(resized_bytes)) as img:
        assert img.size == (400, 200)
        assert img.format == "JPEG"
