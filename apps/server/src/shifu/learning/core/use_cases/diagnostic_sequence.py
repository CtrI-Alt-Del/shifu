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
        available = tuple(
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
        if not skill.initial_diagnostic_activity_ids:
            return available

        by_id = {
            activity.id: (competency_id, activity)
            for competency_id, activity in available
        }
        return tuple(
            by_id[activity_id] for activity_id in skill.initial_diagnostic_activity_ids
        )

    @staticmethod
    def next_item(
        skill: CurriculumSkillSnapshot,
        attempts: tuple[ActivityAttempt, ...],
        evaluations: tuple[ActivityEvaluation, ...],
        diagnostic_run_id: str | None = None,
    ) -> tuple[str, CurriculumActivitySnapshot, ActivityAttempt | None] | None:
        evaluation_by_attempt = {item.attempt_id: item for item in evaluations}
        by_activity: dict[str, ActivityAttempt] = {}
        for attempt in attempts:
            if attempt.kind is ActivityAttemptKind.DIAGNOSTIC and (
                diagnostic_run_id is None
                or attempt.diagnostic_run_id == diagnostic_run_id
            ):
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
