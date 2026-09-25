from datetime import timedelta

from shifu.learning.core.domain.enums import (
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.adaptive_learning_policy import AdaptiveLearningPolicy
from shifu.learning.core.domain.structures.diagnostic_competency_summary import (
    DiagnosticCompetencySummary,
)
from shifu.learning.core.domain.structures.diagnostic_overview import DiagnosticOverview
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.diagnostic_sequence import DiagnosticSequence
from shifu.shared.core.domain.errors import NotFoundError
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider


class GetDiagnosticUseCase:
    _TIMEOUT = timedelta(minutes=5)

    def __init__(
        self,
        database: LearningDatabase,
        curriculum: CurriculumContentProvider,
        clock: ClockProvider,
    ) -> None:
        self._database = database
        self._curriculum = curriculum
        self._clock = clock

    def execute(
        self, account_id: str, goal_id: str, skill_id: str
    ) -> DiagnosticOverview:
        catalog = self._curriculum.get_skill_content(skill_id)
        if catalog is None or catalog.id != skill_id:
            raise NotFoundError
        with self._database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if (
                goal is None
                or goal.account_id != account_id
                or experience is None
                or experience.policy_id != AdaptiveLearningPolicy.policy_id
            ):
                raise NotFoundError
            if experience.status is SkillExperienceStatus.NOT_STARTED:
                return DiagnosticOverview(
                    status=experience.status,
                    next_competency_id=None,
                    next_activity_id=None,
                    pending_attempt_id=None,
                )
            attempts = tuple(
                repositories.activity_attempts.find_many_by_skill_experience_id(
                    experience.id
                )
            )
            evaluations = tuple(
                repositories.activity_evaluations.find_many_by_attempt_ids(
                    tuple(item.id for item in attempts)
                )
            )
            next_item = (
                DiagnosticSequence.next_item(catalog, attempts, evaluations)
                if experience.status is SkillExperienceStatus.DIAGNOSING
                else None
            )
            if next_item is not None:
                competency_id, activity, attempt = next_item
                pending_status = None
                if attempt is not None:
                    evaluation = next(
                        (item for item in evaluations if item.attempt_id == attempt.id),
                        None,
                    )
                    if evaluation is not None:
                        pending_status = evaluation.status
                        if (
                            evaluation.status is ActivityEvaluationStatus.PENDING
                            and self._clock.now()
                            >= evaluation.started_at + self._TIMEOUT
                        ):
                            locked = repositories.activity_evaluations.find_by_attempt_id_for_update(
                                attempt.id
                            )
                            if (
                                locked is not None
                                and locked.status is ActivityEvaluationStatus.PENDING
                                and self._clock.now()
                                >= locked.started_at + self._TIMEOUT
                            ):
                                locked.time_out('evaluation_timeout')
                                repositories.activity_evaluations.update(locked)
                                pending_status = ActivityEvaluationStatus.FAILED
                return DiagnosticOverview(
                    status=experience.status,
                    next_competency_id=competency_id,
                    next_activity_id=activity.id,
                    pending_attempt_id=attempt.id if attempt is not None else None,
                    pending_attempt_status=pending_status,
                )
            if experience.status is SkillExperienceStatus.DIAGNOSING:
                raise NotFoundError
            progress_rows = (
                repositories.competency_progresses.find_many_by_skill_experience_id(
                    experience.id
                )
            )
            progress_by_id = {item.competency_id: item for item in progress_rows}
            focus = next(
                (
                    competency.id
                    for competency in sorted(
                        catalog.competencies, key=lambda item: (item.position, item.id)
                    )
                    if competency.id in progress_by_id
                    and (
                        progress_by_id[competency.id].status
                        is not CompetencyProgressStatus.MASTERED
                        or progress_by_id[competency.id].verification_cause is not None
                    )
                ),
                None,
            )
            return DiagnosticOverview(
                status=experience.status,
                next_competency_id=None,
                next_activity_id=None,
                pending_attempt_id=None,
                focus_competency_id=focus,
                competencies=tuple(
                    DiagnosticCompetencySummary(
                        competency_id=competency.id,
                        competency_name=competency.name,
                        progress=progress_by_id[competency.id].initial_progress,
                    )
                    for competency in sorted(
                        catalog.competencies, key=lambda item: (item.position, item.id)
                    )
                    if competency.id in progress_by_id
                ),
            )
