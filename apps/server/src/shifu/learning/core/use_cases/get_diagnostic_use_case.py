from datetime import timedelta
from decimal import Decimal

from shifu.learning.core.domain.adaptive_learning_policy import AdaptiveLearningPolicy
from shifu.learning.core.domain.enums import (
    ActivityDifficulty,
    ActivityRecommendationType,
)
from shifu.learning.core.domain.enums import (
    ActivityEvaluationStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures.adaptive_recommendation import (
    AdaptiveRecommendation,
)
from shifu.learning.core.domain.structures.adaptive_competency_state import (
    AdaptiveCompetencyState,
)
from shifu.learning.core.domain.structures.adaptive_concept_state import (
    AdaptiveConceptState,
)
from shifu.learning.core.domain.structures.diagnostic_competency_summary import (
    DiagnosticCompetencySummary,
)
from shifu.learning.core.domain.structures.diagnostic_overview import DiagnosticOverview
from shifu.learning.core.domain.structures import SkillRecommendation
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.adaptive_policy_context import AdaptivePolicyContext
from shifu.learning.core.use_cases.diagnostic_sequence import DiagnosticSequence
from shifu.learning.core.use_cases.demonstrated_progress import demonstrated_progress
from shifu.shared.core.domain.errors import ConflictError, NotFoundError
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumSkillSnapshot,
)
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

    def execute(  # noqa: C901
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        diagnostic_run_id: str | None = None,
    ) -> DiagnosticOverview:
        with self._database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if goal is None or goal.account_id != account_id or experience is None:
                raise NotFoundError
            if experience.status is SkillExperienceStatus.NOT_STARTED:
                return DiagnosticOverview(
                    status=experience.status,
                    run_state='requires_entry',
                )
            if experience.status is SkillExperienceStatus.DIAGNOSING:
                if diagnostic_run_id is None:
                    return DiagnosticOverview(
                        status=experience.status,
                        run_state='requires_entry',
                    )
                if diagnostic_run_id != experience.diagnostic_run_id:
                    raise ConflictError
                catalog = self._curriculum.get_skill_content(skill_id)
                if catalog is None or catalog.id != skill_id or not catalog.v2_eligible:
                    raise NotFoundError
                activity_sequence = tuple(
                    (competency_id, activity.id)
                    for competency_id, activity in DiagnosticSequence.ordered(catalog)
                )
                attempts = tuple(
                    repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id(
                        experience.id, diagnostic_run_id
                    )
                )
                evaluations = tuple(
                    repositories.activity_evaluations.find_many_by_attempt_ids(
                        tuple(item.id for item in attempts)
                    )
                )
                next_item = DiagnosticSequence.next_item(
                    catalog, attempts, evaluations, diagnostic_run_id
                )
                if next_item is not None:
                    competency_id, activity, attempt = next_item
                    evaluation = (
                        next(
                            (
                                item
                                for item in evaluations
                                if item.attempt_id == attempt.id
                            ),
                            None,
                        )
                        if attempt is not None
                        else None
                    )
                    pending_status = (
                        evaluation.status if evaluation is not None else None
                    )
                    if (
                        evaluation is not None
                        and evaluation.status is ActivityEvaluationStatus.PENDING
                        and self._clock.now() >= evaluation.started_at + self._TIMEOUT
                    ):
                        locked = repositories.activity_evaluations.find_by_attempt_id_for_update(
                            evaluation.attempt_id
                        )
                        if (
                            locked is not None
                            and locked.status is ActivityEvaluationStatus.PENDING
                            and self._clock.now() >= locked.started_at + self._TIMEOUT
                        ):
                            locked.time_out('evaluation_timeout')
                            repositories.activity_evaluations.update(locked)
                            pending_status = ActivityEvaluationStatus.FAILED
                    return DiagnosticOverview(
                        status=experience.status,
                        run_state='active',
                        activity_sequence=activity_sequence,
                        next_competency_id=competency_id,
                        next_activity_id=activity.id,
                        pending_attempt_id=attempt.id if attempt is not None else None,
                        pending_attempt_status=pending_status,
                    )
                return DiagnosticOverview(
                    status=experience.status,
                    run_state='ready_to_complete',
                    activity_sequence=activity_sequence,
                    ready_to_complete=True,
                )

            catalog = self._curriculum.get_skill_content(skill_id)
            if catalog is None or catalog.id != skill_id:
                raise NotFoundError
            ordered = sorted(
                catalog.competencies, key=lambda item: (item.position, item.id)
            )
            observations = tuple(
                item
                for item in repositories.concept_observations.find_many_by_skill_experience_id(
                    experience.id
                )
                if item.diagnostic
            )
            context = AdaptivePolicyContext.from_skill(catalog)
            policy_result = AdaptiveLearningPolicy().evaluate(
                limited_diagnostic=bool(catalog.initial_diagnostic_activity_ids),
                concepts=context.concepts,
                competency_ids=context.competency_ids,
                activities=context.activities,
                materials=context.materials,
                observations=observations,
                now=self._clock.now(),
            )
            policy_competencies = {
                item.competency_id: item for item in policy_result.competency_states
            }
            policy_concepts = {
                item.concept_id: item for item in policy_result.concept_states
            }
            completion_summary = experience.completion_summary
            completed_competencies = (
                {item.competency_id: item for item in completion_summary.competencies}
                if completion_summary is not None
                else {}
            )
            initial_values_by_competency: dict[str, Decimal | None] = {}
            initial_coverage_by_competency: dict[str, bool] = {}
            for competency in ordered:
                concept_states = tuple(
                    policy_concepts[item.id] for item in competency.concepts
                )
                snapshot = completed_competencies.get(competency.id)
                demonstrated = demonstrated_progress(
                    tuple(item.initial_progress for item in concept_states)
                )
                initial_values_by_competency[competency.id] = (
                    demonstrated
                    if demonstrated is not None
                    else snapshot.initial_progress
                    if snapshot is not None
                    else None
                )
                initial_coverage_by_competency[competency.id] = (
                    snapshot.initial_coverage_complete
                    if snapshot is not None
                    else all(item.coverage_complete for item in concept_states)
                )
            overall_result = demonstrated_progress(
                tuple(item.initial_progress for item in policy_result.concept_states)
            )
            if overall_result is None and completion_summary is not None:
                overall_result = completion_summary.initial_progress
            overall_coverage_complete = (
                completion_summary.initial_coverage_complete
                if completion_summary is not None
                else bool(ordered) and all(initial_coverage_by_competency.values())
            )
            summaries = tuple(
                DiagnosticCompetencySummary(
                    competency_id=competency.id,
                    competency_name=competency.name,
                    position=competency.position,
                    progress=initial_values_by_competency[competency.id],
                    coverage_complete=initial_coverage_by_competency[competency.id],
                    status=policy_competencies[competency.id].status,
                    is_focus=policy_result.focus_competency_id == competency.id,
                    content_released=policy_competencies[
                        competency.id
                    ].content_released,
                )
                for competency in ordered
            )
            initial_recommendation = self._initial_recommendation(
                catalog,
                policy_result.recommendation,
                policy_competencies,
                policy_concepts,
            )
            initial_recommendation_gap = (
                policy_result.recommendation.gap
                if initial_recommendation is None
                and policy_result.recommendation is not None
                else None
            )
            direct_completion = (
                experience.status is SkillExperienceStatus.COMPLETED
                and completion_summary is not None
                and completion_summary.initial_progress
                == completion_summary.final_progress
            )
            return DiagnosticOverview(
                status=experience.status,
                run_state='settled',
                focus_competency_id=policy_result.focus_competency_id,
                competencies=summaries,
                initial_overall_result=overall_result,
                overall_coverage_complete=overall_coverage_complete,
                direct_completion=direct_completion,
                initial_recommendation=initial_recommendation,
                initial_recommendation_gap=initial_recommendation_gap,
            )

    @staticmethod
    def _initial_recommendation(
        catalog: CurriculumSkillSnapshot,
        recommendation: AdaptiveRecommendation | None,
        competencies: dict[str, AdaptiveCompetencyState],
        concepts: dict[str, AdaptiveConceptState],
    ) -> SkillRecommendation | None:
        if recommendation is None:
            return None

        # Concrete curriculum types are kept at the boundary so the serialized
        # recommendation stays aligned with GetSkillExperienceDetailUseCase.
        selected_activity = next(
            (
                item
                for competency_item in catalog.competencies
                for item in competency_item.items
                if isinstance(item, CurriculumActivitySnapshot)
                and item.id == recommendation.activity_id
            ),
            None,
        )
        fallback_selected = False
        if (
            selected_activity is None
            and recommendation.activity_id is None
            and recommendation.gap == 'curriculum_or_assessment_unavailable'
        ):
            selected_activity = GetDiagnosticUseCase._fallback_initial_activity(
                catalog,
                recommendation,
                competencies,
                concepts,
            )
            fallback_selected = selected_activity is not None
        if selected_activity is None:
            return None
        catalog_competencies = catalog.competencies
        selected_competency_id = recommendation.competency_id
        if fallback_selected:
            selected_competency_id = next(
                (
                    item.id
                    for item in catalog_competencies
                    if any(
                        isinstance(activity, CurriculumActivitySnapshot)
                        and activity.id == selected_activity.id
                        for activity in item.items
                    )
                ),
                '',
            )
        competency = next(
            (
                item
                for item in catalog_competencies
                if item.id == selected_competency_id
            ),
            None,
        )
        if competency is None:
            return None
        target_concept_name = next(
            (
                item.name
                for current_competency in catalog_competencies
                for item in current_competency.concepts
                if item.id == recommendation.target_concept_id
            ),
            None,
        )
        return SkillRecommendation(
            competency_id=competency.id,
            competency_name=competency.name,
            activity_id=selected_activity.id,
            activity_title=selected_activity.title,
            difficulty=ActivityDifficulty(selected_activity.difficulty),
            type=ActivityRecommendationType.NEW_ACTIVITY,
            reason=recommendation.reason,
            target_concept_name=target_concept_name,
            material_id=recommendation.material_id,
            gap=None if fallback_selected else recommendation.gap,
        )

    @staticmethod
    def _fallback_initial_activity(
        catalog: CurriculumSkillSnapshot,
        recommendation: AdaptiveRecommendation,
        competencies: dict[str, AdaptiveCompetencyState],
        concepts: dict[str, AdaptiveConceptState],
    ) -> CurriculumActivitySnapshot | None:
        target_concept_id = recommendation.target_concept_id
        if recommendation.difficulty is None:
            return None
        focus = competencies.get(recommendation.competency_id)
        hard_required = focus is not None and focus.verification_cause == 'hard'
        difficulty_order = {
            ActivityDifficulty.EASY: 0,
            ActivityDifficulty.MEDIUM: 1,
            ActivityDifficulty.HARD: 2,
        }
        preferred = difficulty_order[recommendation.difficulty]
        candidates = tuple(
            item
            for competency in catalog.competencies
            if (state := competencies.get(competency.id)) is not None
            and state.content_released
            for item in competency.items
            if isinstance(item, CurriculumActivitySnapshot)
            and item.activity_type == 'learning'
            and target_concept_id in item.concept_ids
            and item.executable_concept_evidence
            and (not hard_required or item.difficulty == ActivityDifficulty.HARD.value)
            and not any(
                (required := concepts.get(required_id)) is not None
                and (
                    required.progress is None
                    or required.progress < Decimal('70')
                    or len(required.distinct_activity_ids) < 2
                    or required.evidence_verification
                )
                for required_id in item.required_concept_ids
            )
        )
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda item: (
                abs(difficulty_order[ActivityDifficulty(item.difficulty)] - preferred),
                difficulty_order[ActivityDifficulty(item.difficulty)] > preferred,
                item.position,
                item.id,
            ),
        )
