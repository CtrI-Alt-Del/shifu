from decimal import Decimal
from typing import cast

from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.learning.core.domain.structures import ConceptObservation
from shifu.learning.database.sqlalchemy.models.concept_observation_model import (
    ConceptObservationModel,
)


class ConceptObservationMapper:
    @staticmethod
    def to_domain(model: ConceptObservationModel) -> ConceptObservation:
        scores = cast('list[str | None]', model.question_scores)
        return ConceptObservation(
            attempt_id=model.attempt_id,
            activity_id=model.activity_id,
            concept_id=model.concept_id,
            difficulty=ActivityDifficulty(model.difficulty),
            first_submitted_at=model.first_submitted_at,
            submitted_at=model.submitted_at,
            completed_at=model.completed_at,
            question_scores=tuple(
                Decimal(score) if score is not None else None for score in scores
            ),
            diagnostic=model.diagnostic,
        )

    @staticmethod
    def to_model(
        skill_experience_id: str,
        competency_id: str,
        observation: ConceptObservation,
    ) -> ConceptObservationModel:
        return ConceptObservationModel(
            attempt_id=observation.attempt_id,
            concept_id=observation.concept_id,
            skill_experience_id=skill_experience_id,
            competency_id=competency_id,
            activity_id=observation.activity_id,
            difficulty=observation.difficulty.value,
            first_submitted_at=observation.first_submitted_at,
            submitted_at=observation.submitted_at,
            completed_at=observation.completed_at,
            question_scores=[
                str(score) if score is not None else None
                for score in observation.question_scores
            ],
            diagnostic=observation.diagnostic,
        )
