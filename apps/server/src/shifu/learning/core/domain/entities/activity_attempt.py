from datetime import datetime

from shifu.learning.core.domain.enums import ActivityAttemptKind
from shifu.learning.core.domain.structures import ActivityAnswer
from shifu.shared.core.domain.structures import CurriculumChoiceActivitySnapshot
from shifu.shared.core.domain.entities import frozen_entity


@frozen_entity
class ActivityAttempt:
    id: str
    skill_experience_id: str
    competency_id: str
    activity_id: str
    kind: ActivityAttemptKind
    answers: tuple[ActivityAnswer, ...]
    submitted_at: datetime
    submission_key: str | None = None
    grading_snapshot: CurriculumChoiceActivitySnapshot | None = None

    @classmethod
    def create(
        cls,
        *,
        id: str,
        skill_experience_id: str,
        competency_id: str,
        activity_id: str,
        kind: ActivityAttemptKind,
        answers: tuple[ActivityAnswer, ...],
        submitted_at: datetime,
        submission_key: str | None = None,
        grading_snapshot: CurriculumChoiceActivitySnapshot | None = None,
    ) -> 'ActivityAttempt':
        return cls(
            id=id,
            skill_experience_id=skill_experience_id,
            competency_id=competency_id,
            activity_id=activity_id,
            kind=kind,
            answers=answers,
            submitted_at=submitted_at,
            submission_key=submission_key,
            grading_snapshot=grading_snapshot,
        )
