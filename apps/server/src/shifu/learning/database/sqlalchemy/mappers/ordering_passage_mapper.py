from typing import TYPE_CHECKING, Literal, cast

from shifu.learning.core.domain.entities.ordering_passage import OrderingPassage
from shifu.learning.core.domain.structures.verified_ordering import VerifiedOrdering
from shifu.learning.database.sqlalchemy.models import OrderingPassageModel
from shifu.learning.database.sqlalchemy.mappers.activity_attempt_mapper import (
    ActivityAttemptMapper,
)
from shifu.shared.database.sqlalchemy.serialization import Serialization

if TYPE_CHECKING:
    from shifu.shared.core.domain.structures import CurriculumLearningActivitySnapshot


class OrderingPassageMapper:
    @staticmethod
    def to_domain(model: OrderingPassageModel) -> OrderingPassage:
        if model.schema_version != 1:
            raise TypeError('Stored ordering passage schema version is unsupported.')

        snapshot = ActivityAttemptMapper.snapshot_to_domain(model.grading_snapshot)
        verified = tuple(
            Serialization.deserialize_value(item, VerifiedOrdering)
            for item in cast('list[object]', model.verified_orderings)
        )
        return OrderingPassage(
            id=model.id,
            skill_experience_id=model.skill_experience_id,
            activity_id=model.activity_id,
            passage_key=model.passage_key,
            activity_revision=model.activity_revision,
            grading_snapshot=cast('CurriculumLearningActivitySnapshot', snapshot),
            verified_orderings=cast('tuple[VerifiedOrdering, ...]', verified),
            status=cast("Literal['active', 'consumed']", model.status),
        )

    @staticmethod
    def to_model(passage: OrderingPassage) -> OrderingPassageModel:
        return OrderingPassageModel(
            id=passage.id,
            skill_experience_id=passage.skill_experience_id,
            activity_id=passage.activity_id,
            passage_key=passage.passage_key,
            activity_revision=passage.activity_revision,
            grading_snapshot=Serialization.serialize_value(passage.grading_snapshot),
            verified_orderings=Serialization.serialize_value(
                passage.verified_orderings
            ),
            schema_version=1,
            status=passage.status,
        )
