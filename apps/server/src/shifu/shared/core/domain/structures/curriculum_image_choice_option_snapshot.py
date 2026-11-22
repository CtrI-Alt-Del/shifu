import re

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure

_KEY_PATTERN = re.compile(r'opt-[0-9a-f]{12}')
_IMAGE_PATH_PATTERN = re.compile(r'/curriculum/images/[0-9a-f]{16}\.webp')


@structure
class CurriculumImageChoiceOptionSnapshot:
    key: str
    image_path: str
    description: str
    is_correct: bool
    feedback: str

    def __post_init__(self) -> None:
        for name in ('key', 'image_path', 'description', 'feedback'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=ValidationError
                ).value,
            )

        if (
            _KEY_PATTERN.fullmatch(self.key) is None
            or _IMAGE_PATH_PATTERN.fullmatch(self.image_path) is None
        ):
            raise ValidationError
