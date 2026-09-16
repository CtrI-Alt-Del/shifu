from typing import cast

from shifu.curriculum.core.domain.structures import CurriculumSequence
from shifu.curriculum.core.domain.structures import CurriculumSequenceItem
from shifu.curriculum.database.sqlalchemy.models import CurriculumSequenceModel
from shifu.shared.database.sqlalchemy.serialization import (
    deserialize_value,
    serialize_value,
)


class CurriculumSequenceMapper:
    @staticmethod
    def to_domain(model: CurriculumSequenceModel) -> CurriculumSequence:
        return CurriculumSequence(
            competency_id=model.competency_id,
            items=cast(
                'tuple[CurriculumSequenceItem, ...]',
                deserialize_value(
                    model.items,
                    tuple[CurriculumSequenceItem, ...],
                ),
            ),
        )

    @staticmethod
    def to_model(sequence: CurriculumSequence) -> CurriculumSequenceModel:
        return CurriculumSequenceModel(
            competency_id=sequence.competency_id,
            items=serialize_value(sequence.items),
        )
