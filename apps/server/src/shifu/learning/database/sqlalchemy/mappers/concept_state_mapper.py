from decimal import Decimal
from typing import cast

from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.learning.core.domain.structures import AdaptiveConceptState
from shifu.learning.database.sqlalchemy.models.concept_state_model import (
    ConceptStateModel,
)


class ConceptStateMapper:
    @staticmethod
    def to_domain(model: ConceptStateModel) -> AdaptiveConceptState:
        contributions = cast('list[list[str]]', model.current_contributions)
        return AdaptiveConceptState(
            concept_id=model.concept_id,
            initial_progress=model.initial_progress,
            progress=model.current_progress,
            observed_difficulties=frozenset(
                ActivityDifficulty(value)
                for value in cast('list[str]', model.observed_difficulties)
            ),
            distinct_activity_ids=frozenset(
                cast('list[str]', model.distinct_activity_ids)
            ),
            hard_confirmation=model.hard_confirmation,
            evidence_verification=model.evidence_verification,
            inconclusive_activity_ids=tuple(
                cast('list[str]', model.inconclusive_activity_ids)
            ),
            current_contributions=tuple(
                (activity_id, Decimal(score)) for activity_id, score in contributions
            ),
        )

    @staticmethod
    def to_model(
        skill_experience_id: str,
        competency_id: str,
        state: AdaptiveConceptState,
        updated_at: object,
    ) -> ConceptStateModel:
        from datetime import datetime

        if not isinstance(updated_at, datetime):
            raise TypeError('Concept state update time must be a datetime.')
        return ConceptStateModel(
            skill_experience_id=skill_experience_id,
            concept_id=state.concept_id,
            competency_id=competency_id,
            initial_progress=state.initial_progress,
            current_progress=state.progress,
            observed_difficulties=sorted(
                item.value for item in state.observed_difficulties
            ),
            distinct_activity_ids=sorted(state.distinct_activity_ids),
            hard_confirmation=state.hard_confirmation,
            evidence_verification=state.evidence_verification,
            inconclusive_activity_ids=list(state.inconclusive_activity_ids),
            current_contributions=[
                [activity_id, str(score)]
                for activity_id, score in state.current_contributions
            ],
            updated_at=updated_at,
        )
