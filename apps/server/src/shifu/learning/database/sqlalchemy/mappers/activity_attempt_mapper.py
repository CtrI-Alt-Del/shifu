from typing import cast

from shifu.learning.core.domain.entities import ActivityAttempt
from shifu.learning.core.domain.enums import ActivityAttemptKind
from shifu.learning.core.domain.structures import ActivityAnswer
from shifu.learning.database.sqlalchemy.models import ActivityAttemptModel
from shifu.shared.database.sqlalchemy.serialization import Serialization


class ActivityAttemptMapper:
    @staticmethod
    def to_domain(model: ActivityAttemptModel) -> ActivityAttempt:
        return ActivityAttempt(
            id=model.id,
            skill_experience_id=model.skill_experience_id,
            competency_id=model.competency_id,
            activity_id=model.activity_id,
            kind=ActivityAttemptKind(model.kind),
            answers=cast(
                'tuple[ActivityAnswer, ...]',
                Serialization.deserialize_value(
                    model.answers, tuple[ActivityAnswer, ...]
                ),
            ),
            submitted_at=model.submitted_at,
        )

    @staticmethod
    def to_model(attempt: ActivityAttempt) -> ActivityAttemptModel:
        return ActivityAttemptModel(
            id=attempt.id,
            skill_experience_id=attempt.skill_experience_id,
            competency_id=attempt.competency_id,
            activity_id=attempt.activity_id,
            kind=attempt.kind.value,
            answers=Serialization.serialize_value(attempt.answers),
            submitted_at=attempt.submitted_at,
        )
