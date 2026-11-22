from dataclasses import field

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.curriculum_practical_preparation_criterion_snapshot import (
    CurriculumPracticalPreparationCriterionSnapshot,
)
from shifu.shared.core.domain.structures.curriculum_practical_preparation_record_snapshot import (
    CurriculumPracticalPreparationRecordSnapshot,
)
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure

PRACTICE_PHOTO_MEDIA_TYPES = ('image/jpeg', 'image/png', 'image/webp')


@structure
class PracticePhotoAssessmentPhoto:
    """One photo for one record. The bytes never appear in repr or logs."""

    record_key: str
    media_type: str
    content: bytes = field(repr=False)

    def __post_init__(self) -> None:
        NonEmptyText.create(self.record_key, error_type=ValidationError)
        if self.media_type not in PRACTICE_PHOTO_MEDIA_TYPES or not self.content:
            raise ValidationError


@structure
class PracticePhotoAssessmentInput:
    """Minimum context for the assessor: no account, attempt or object identifiers."""

    prompt: str
    records: tuple[CurriculumPracticalPreparationRecordSnapshot, ...]
    criteria: tuple[CurriculumPracticalPreparationCriterionSnapshot, ...]
    photos: tuple[PracticePhotoAssessmentPhoto, ...]

    def __post_init__(self) -> None:
        NonEmptyText.create(self.prompt, error_type=ValidationError)
        record_keys = tuple(record.key for record in self.records)
        photo_keys = tuple(photo.record_key for photo in self.photos)
        if (
            not self.records
            or not self.criteria
            or len(record_keys) != len(set(record_keys))
            or sorted(photo_keys) != sorted(record_keys)
        ):
            raise ValidationError
