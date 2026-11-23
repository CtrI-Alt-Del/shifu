import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from shifu.learning.core.domain.errors import PracticePhotoInvalidError

_FORMATS = {
    'image/jpeg': 'JPEG',
    'image/png': 'PNG',
    'image/webp': 'WEBP',
}
_MAX_PIXELS = 20_000_000


class PillowPracticePhotoInspectorProvider:
    """Decode practice photos locally and enforce the declared format and pixel limit."""

    def __init__(self, max_pixels: int = _MAX_PIXELS) -> None:
        self._max_pixels = max_pixels

    def sanitize(self, content: bytes, media_type: str) -> bytes:
        expected_format = _FORMATS.get(media_type)
        if expected_format is None or not content:
            raise PracticePhotoInvalidError

        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(content)) as image:
                    self._assert_acceptable(image, expected_format)
                    image.verify()
                with Image.open(io.BytesIO(content)) as image:
                    self._assert_acceptable(image, expected_format)
                    image.load()
                    # Apply the EXIF orientation, then re-encode without any metadata.
                    oriented = ImageOps.exif_transpose(image)
                    return self._encode(oriented, expected_format)
        except (
            UnidentifiedImageError,
            OSError,
            SyntaxError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as error:
            raise PracticePhotoInvalidError from error

    @staticmethod
    def _encode(image: Image.Image, image_format: str) -> bytes:
        buffer = io.BytesIO()
        if image_format == 'PNG':
            image.save(buffer, format='PNG', optimize=True)
        else:
            if image_format == 'JPEG' and image.mode not in {'RGB', 'L', 'CMYK'}:
                image = image.convert('RGB')
            image.save(buffer, format=image_format, quality=95)
        return buffer.getvalue()

    def _assert_acceptable(self, image: Image.Image, expected_format: str) -> None:
        if (
            image.format != expected_format
            or image.width < 1
            or image.height < 1
            or image.width * image.height > self._max_pixels
        ):
            raise PracticePhotoInvalidError
