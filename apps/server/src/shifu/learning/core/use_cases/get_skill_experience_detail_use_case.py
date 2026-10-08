from decimal import Decimal

from shifu.learning.core.domain.entities import CompetencyProgress
from shifu.learning.core.domain.enums import (
    ActivityRecommendationType,
    CompetencyAvailability,
)
from shifu.learning.core.domain.errors import SkillExperienceDetailNotFoundError
from shifu.learning.core.domain.structures import (
    AdaptiveConceptState,
    AvailableCompetencyDetail,
    SkillCompetencySummary,
    SkillEvaluationState,
    SkillExperienceDetail,
    SkillRecommendation,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.get_competency_detail_use_case import (
    GetCompetencyDetailUseCase,
)
from shifu.learning.core.use_cases.demonstrated_progress import demonstrated_progress
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumCompetencySnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider


class GetSkillExperienceDetailUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        get_competency_detail_use_case: GetCompetencyDetailUseCase,
    ) -> None:
        self._learning_database = learning_database
        self._curriculum_content_provider = curriculum_content_provider
        self._get_competency_detail_use_case = get_competency_detail_use_case

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
    ) -> SkillExperienceDetail:
        with self._learning_database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            if goal is None or goal.id != goal_id or goal.account_id != account_id:
                raise SkillExperienceDetailNotFoundError

            skill_experience = (
                repositories.skill_experiences.find_by_goal_id_and_skill_id(
                    goal_id,
                    skill_id,
                )
            )
            if (
                skill_experience is None
                or skill_experience.goal_id != goal_id
                or skill_experience.skill_id != skill_id
            ):
                raise SkillExperienceDetailNotFoundError

            skill_content = self._curriculum_content_provider.get_skill_content(
                skill_id
            )
            if skill_content is None or skill_content.id != skill_id:
                raise SkillExperienceDetailNotFoundError

            competencies = tuple(
                sorted(skill_content.competencies, key=lambda item: item.position)
            )
            progress_rows = (
                repositories.competency_progresses.find_many_by_skill_experience_id(
                    skill_experience.id
                )
            )
            progress_by_competency = {
                progress.competency_id: progress
                for progress in progress_rows
                if progress.skill_experience_id == skill_experience.id
            }
            concept_states = {
                state.concept_id: state
                for state in repositories.concept_states.find_many_by_skill_experience_id(
                    skill_experience.id
                )
            }
            focus = GetCompetencyDetailUseCase.find_focus(
                competencies,
                progress_by_competency,
            )
            summaries = self._summarize(
                competencies, progress_by_competency, concept_states, focus
            )
            evaluation = self._held_evaluation(repositories, skill_experience.id)
            activity_titles = self._activity_titles(competencies)
            skill_name = skill_content.name
            skill_status = skill_experience.status

        recommendation = (
            self._focus_recommendation(
                account_id,
                goal_id,
                skill_id,
                focus,
                activity_titles,
            )
            if focus is not None and evaluation is None
            else None
        )

        return SkillExperienceDetail(
            goal_id=goal_id,
            skill_id=skill_id,
            skill_name=skill_name,
            skill_status=skill_status,
            overall_result=(
                demonstrated_progress(
                    tuple(
                        concept_states[item.id].progress
                        if item.id in concept_states
                        else None
                        for competency in competencies
                        for item in competency.concepts
                    )
                )
                if concept_states
                else self._overall_result(summaries)
            ),
            focus_competency_id=focus.id if focus is not None else None,
            focus_competency_name=focus.name if focus is not None else None,
            competencies=summaries,
            recommendation=recommendation,
            evaluation=evaluation,
            overall_coverage_complete=bool(summaries)
            and all(item.coverage_complete for item in summaries),
            recommendation_gap=(
                recommendation.gap if recommendation is not None else None
            ),
        )

    def _focus_recommendation(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        focus: CurriculumCompetencySnapshot,
        activity_titles: dict[str, str],
    ) -> SkillRecommendation | None:
        detail = self._get_competency_detail_use_case.execute(
            account_id,
            goal_id,
            skill_id,
            focus.id,
        )
        if not isinstance(detail, AvailableCompetencyDetail):
            return None

        recommendation = detail.recommendation
        adaptive = detail.adaptive
        if adaptive is not None:
            if adaptive.activity_id is None or adaptive.difficulty is None:
                return None

            return SkillRecommendation(
                competency_id=focus.id,
                competency_name=focus.name,
                activity_id=adaptive.activity_id,
                activity_title=activity_titles.get(adaptive.activity_id, ''),
                difficulty=adaptive.difficulty,
                type=ActivityRecommendationType.NEW_ACTIVITY,
                reason=adaptive.reason,
                target_concept_name=adaptive.target_concept_name,
                material_id=adaptive.material_id,
                gap=adaptive.gap,
            )

        if recommendation is None:
            return None

        return SkillRecommendation(
            competency_id=recommendation.competency_id,
            competency_name=focus.name,
            activity_id=recommendation.activity_id,
            activity_title=activity_titles.get(recommendation.activity_id, ''),
            difficulty=recommendation.difficulty,
            type=recommendation.type,
            reason=recommendation.type.value,
        )

    @staticmethod
    def _activity_titles(
        competencies: tuple[CurriculumCompetencySnapshot, ...],
    ) -> dict[str, str]:
        titles: dict[str, str] = {}
        for competency in competencies:
            for item in competency.items:
                if isinstance(item, CurriculumActivitySnapshot):
                    titles[item.id] = item.title
        return titles

    @staticmethod
    def _summarize(
        competencies: tuple[CurriculumCompetencySnapshot, ...],
        progress_by_competency: dict[str, CompetencyProgress],
        concept_states: dict[str, AdaptiveConceptState],
        focus: CurriculumCompetencySnapshot | None,
    ) -> tuple[SkillCompetencySummary, ...]:
        summaries: list[SkillCompetencySummary] = []
        for competency in competencies:
            progress = progress_by_competency.get(competency.id)
            released = progress is not None and progress.content_released
            summaries.append(
                SkillCompetencySummary(
                    competency_id=competency.id,
                    competency_name=competency.name,
                    position=competency.position,
                    progress=(
                        demonstrated_progress(
                            tuple(
                                concept_states[item.id].progress
                                if item.id in concept_states
                                else None
                                for item in competency.concepts
                            )
                        )
                        if any(
                            item.id in concept_states for item in competency.concepts
                        )
                        else progress.current_progress
                        if progress is not None
                        and progress.current_progress is not None
                        else progress.initial_progress
                        if progress is not None
                        else None
                    ),
                    status=(progress.status if progress is not None else None),
                    availability=(
                        CompetencyAvailability.AVAILABLE
                        if released
                        else CompetencyAvailability.UNAVAILABLE
                    ),
                    is_focus=focus is not None and focus.id == competency.id,
                    coverage_complete=(
                        progress.coverage_complete if progress is not None else False
                    ),
                )
            )
        return tuple(summaries)

    @staticmethod
    def _overall_result(
        summaries: tuple[SkillCompetencySummary, ...],
    ) -> Decimal | None:
        if not summaries:
            return None

        known = tuple(item.progress for item in summaries if item.progress is not None)
        if not known:
            return None

        total = sum(
            known,
            start=Decimal('0'),
        )
        return total / Decimal(len(known))

    @staticmethod
    def _held_evaluation(
        repositories: LearningDatabaseRepositories,
        skill_experience_id: str,
    ) -> SkillEvaluationState | None:
        evaluations = repositories.activity_evaluations
        evaluation = evaluations.find_unresolved_by_skill_experience_id(
            skill_experience_id
        )
        if evaluation is None:
            return None

        attempt = repositories.activity_attempts.find_by_id(evaluation.attempt_id)
        if attempt is None or attempt.skill_experience_id != skill_experience_id:
            return None

        return SkillEvaluationState(
            evaluation_id=evaluation.id,
            attempt_id=attempt.id,
            activity_id=attempt.activity_id,
            competency_id=attempt.competency_id,
            status=evaluation.status,
        )
