from shifu.learning.core.domain.entities import ActivityAttempt, ActivityEvaluation
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
)
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumSkillSnapshot,
)


class DiagnosticSequence:
    @staticmethod
    def ordered(
        skill: CurriculumSkillSnapshot,
    ) -> tuple[tuple[str, CurriculumActivitySnapshot], ...]:
        levels = {'easy': 0, 'medium': 1, 'hard': 2}
        return tuple(
            (competency.id, activity)
            for competency in sorted(
                skill.competencies, key=lambda item: (item.position, item.id)
            )
            for activity in sorted(
                competency.diagnostic_activities,
                key=lambda item: (
                    levels.get(item.difficulty, 3),
                    item.position,
                    item.id,
                ),
            )
        )

    @staticmethod
    def next_item(
        skill: CurriculumSkillSnapshot,
        attempts: tuple[ActivityAttempt, ...],
        evaluations: tuple[ActivityEvaluation, ...],
    ) -> tuple[str, CurriculumActivitySnapshot, ActivityAttempt | None] | None:
        evaluation_by_attempt = {item.attempt_id: item for item in evaluations}
        by_activity: dict[str, ActivityAttempt] = {}
        for attempt in attempts:
            if attempt.kind is ActivityAttemptKind.DIAGNOSTIC:
                by_activity[attempt.activity_id] = attempt
        for competency_id, activity in DiagnosticSequence.ordered(skill):
            attempt = by_activity.get(activity.id)
            evaluation = (
                evaluation_by_attempt.get(attempt.id) if attempt is not None else None
            )
            if (
                evaluation is None
                or evaluation.status is not ActivityEvaluationStatus.COMPLETED
            ):
                return competency_id, activity, attempt
        return None
