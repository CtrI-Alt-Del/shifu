from decimal import Decimal
from typing import Literal

from shifu.shared.core.domain.structures import structure


@structure
class PracticalPreparationReferenceDetail:
    label: str
    accessible_text: str


@structure
class PracticalPreparationRecordDetail:
    key: str
    label: str
    must_show: str


@structure
class PracticalPreparationCriterionDetail:
    key: str
    name: str
    description: str
    weight: Decimal


@structure
class PracticalPreparationQuestionDetail:
    """Public projection: it never carries levels, comments or insufficiency rules."""

    key: str
    prompt: str
    guidance: tuple[str, ...]
    references: tuple[PracticalPreparationReferenceDetail, ...]
    difficulty: str
    records: tuple[PracticalPreparationRecordDetail, ...]
    criteria: tuple[PracticalPreparationCriterionDetail, ...]
    kind: Literal['practical_preparation'] = 'practical_preparation'
