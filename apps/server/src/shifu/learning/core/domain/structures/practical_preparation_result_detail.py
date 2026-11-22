from decimal import Decimal
from typing import Literal

from shifu.shared.core.domain.structures import structure


@structure
class PracticalResultRecordDetail:
    key: str
    label: str


@structure
class PracticalResultPhotoDetail:
    record_key: str
    photo_id: str


@structure
class PracticalResultCriterionDetail:
    key: str
    name: str
    weight: Decimal
    level: int | None
    comment: str | None


@structure
class PracticalUnassessableRecordDetail:
    key: str
    label: str
    comment: str


@structure
class PracticalPreparationResultDetail:
    question_key: str
    prompt: str
    records: tuple[PracticalResultRecordDetail, ...]
    photos: tuple[PracticalResultPhotoDetail, ...]
    reflection: str
    criteria: tuple[PracticalResultCriterionDetail, ...]
    score: Decimal | None
    closed_without_grade: bool
    unassessable_records: tuple[PracticalUnassessableRecordDetail, ...]
    guidance: str | None
    kind: Literal['practical_preparation'] = 'practical_preparation'
