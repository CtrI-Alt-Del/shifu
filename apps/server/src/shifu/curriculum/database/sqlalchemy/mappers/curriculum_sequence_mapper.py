from typing import cast

from shifu.curriculum.core.domain.structures import ActivitySequenceItem
from shifu.curriculum.core.domain.structures import CurriculumSequence
from shifu.curriculum.core.domain.structures import MaterialSequenceItem
from shifu.curriculum.database.sqlalchemy.models import CurriculumSequenceModel
from shifu.shared.database.sqlalchemy.serialization import Serialization


class CurriculumSequenceMapper:
    @staticmethod
    def to_domain(model: CurriculumSequenceModel) -> CurriculumSequence:
        return CurriculumSequence(
            competency_id=model.competency_id,
            items=cast(
                'tuple[MaterialSequenceItem | ActivitySequenceItem, ...]',
                Serialization.deserialize_value(
                    model.items,
                    tuple[MaterialSequenceItem | ActivitySequenceItem, ...],
                ),
            ),
        )

    @staticmethod
    def to_model(sequence: CurriculumSequence) -> CurriculumSequenceModel:
        return CurriculumSequenceModel(
            competency_id=sequence.competency_id,
            items=Serialization.serialize_value(sequence.items),
        )
