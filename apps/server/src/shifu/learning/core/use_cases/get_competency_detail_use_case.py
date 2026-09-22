from decimal import Decimal

from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    CompetencyProgress,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityDifficulty,
    ActivityEvaluationStatus,
    ActivityRecommendationType,
    CompetencyAvailability,
    CompetencyProgressStatus,
)
from shifu.learning.core.domain.errors import CompetencyDetailNotFoundError
from shifu.learning.core.domain.structures import (
    ActivityRecommendation,
    AvailableCompetencyDetail,
    CompetencyActivityDetail,
    CompetencyDetail,
    CompetencyMaterialDetail,
    OfficialActivityResult,
    UnavailableCompetencyDetail,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumCompetencySnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider


class GetCompetencyDetailUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
    ) -> None:
        self._learning_database = learning_database
        self._curriculum_content_provider = curriculum_content_provider

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
    ) -> CompetencyDetail:
        with self._learning_database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            if goal is None or goal.id != goal_id or goal.account_id != account_id:
                raise CompetencyDetailNotFoundError

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
                raise CompetencyDetailNotFoundError

            skill_content = self._curriculum_content_provider.get_skill_content(
                skill_id
            )
            if skill_content is None or skill_content.id != skill_id:
                raise CompetencyDetailNotFoundError

            competencies = self._ordered_competencies(skill_content)
            competency = next(
                (
                    candidate
                    for candidate in competencies
                    if candidate.id == competency_id and candidate.skill_id == skill_id
                ),
                None,
            )
            if competency is None:
                raise CompetencyDetailNotFoundError

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
            focus = self._find_focus(competencies, progress_by_competency)
            focus_competency_id = focus.id if focus is not None else None
            focus_competency_name = focus.name if focus is not None else None
            requested_progress = progress_by_competency.get(competency.id)

            if requested_progress is None or not requested_progress.content_released:
                return UnavailableCompetencyDetail(
                    goal_id=goal_id,
                    skill_id=skill_id,
                    skill_name=skill_content.name,
                    competency_id=competency.id,
                    competency_name=competency.name,
                    availability=CompetencyAvailability.UNAVAILABLE,
                    focus_competency_id=focus_competency_id,
                    focus_competency_name=focus_competency_name,
                )

            attempts = repositories.activity_attempts.find_many_by_skill_experience_id(
                skill_experience.id
            )
            learning_attempts = tuple(
                attempt
                for attempt in attempts
                if attempt.skill_experience_id == skill_experience.id
                and attempt.competency_id == competency.id
                and attempt.kind is ActivityAttemptKind.LEARNING
            )
            evaluations = repositories.activity_evaluations.find_many_by_attempt_ids(
                tuple(attempt.id for attempt in learning_attempts)
            )
            latest_results = self._latest_official_results(
                learning_attempts,
                evaluations,
            )
            items = self._build_items(competency, latest_results)
            is_focus = focus is not None and focus.id == competency.id
            focus_returned = is_focus and self._has_later_released_competency(
                competency,
                competencies,
                progress_by_competency,
            )
            recommendation = (
                self._recommend(
                    competency,
                    requested_progress,
                    items,
                    learning_attempts,
                    latest_results,
                )
                if is_focus
                else None
            )

            return AvailableCompetencyDetail(
                goal_id=goal_id,
                skill_id=skill_id,
                skill_name=skill_content.name,
                competency_id=competency.id,
                competency_name=competency.name,
                availability=CompetencyAvailability.AVAILABLE,
                progress=self._display_progress(requested_progress),
                status=requested_progress.status or CompetencyProgressStatus.LEARNING,
                is_focus=is_focus,
                focus_returned=focus_returned,
                focus_competency_id=focus_competency_id,
                focus_competency_name=focus_competency_name,
                items=items,
                recommendation=recommendation,
            )

    @staticmethod
    def _ordered_competencies(
        skill_content: CurriculumSkillSnapshot,
    ) -> tuple[CurriculumCompetencySnapshot, ...]:
        return tuple(sorted(skill_content.competencies, key=lambda item: item.position))

    @staticmethod
    def _find_focus(
        competencies: tuple[CurriculumCompetencySnapshot, ...],
        progress_by_competency: dict[str, CompetencyProgress],
    ) -> CurriculumCompetencySnapshot | None:
        for competency in competencies:
            progress = progress_by_competency.get(competency.id)
            if (
                progress is None
                or progress.status is not CompetencyProgressStatus.MASTERED
            ):
                return competency
        return None

    @staticmethod
    def _display_progress(progress: CompetencyProgress) -> Decimal:
        if progress.current_progress is not None:
            return progress.current_progress
        if progress.initial_progress is not None:
            return progress.initial_progress
        return Decimal('0')

    @staticmethod
    def _latest_official_results(
        attempts: tuple[ActivityAttempt, ...],
        evaluations: list[ActivityEvaluation],
    ) -> dict[str, OfficialActivityResult]:
        evaluations_by_attempt_id = {
            evaluation.attempt_id: evaluation for evaluation in evaluations
        }
        latest_results: dict[str, OfficialActivityResult] = {}
        for attempt in attempts:
            evaluation = evaluations_by_attempt_id.get(attempt.id)
            if (
                evaluation is None
                or evaluation.status is not ActivityEvaluationStatus.COMPLETED
                or evaluation.score is None
                or evaluation.completed_at is None
            ):
                continue
            latest_results[attempt.activity_id] = OfficialActivityResult(
                activity_id=attempt.activity_id,
                attempt_id=attempt.id,
                score=evaluation.score,
                submitted_at=attempt.submitted_at,
                completed_at=evaluation.completed_at,
            )
        return latest_results

    @staticmethod
    def _build_items(
        competency: CurriculumCompetencySnapshot,
        latest_results: dict[str, OfficialActivityResult],
    ) -> tuple[CompetencyMaterialDetail | CompetencyActivityDetail, ...]:
        items: list[CompetencyMaterialDetail | CompetencyActivityDetail] = []
        for item in sorted(competency.items, key=lambda content: content.position):
            if isinstance(item, CurriculumActivitySnapshot):
                items.append(
                    CompetencyActivityDetail(
                        id=item.id,
                        title=item.title,
                        position=item.position,
                        activity_type=item.activity_type,
                        difficulty=ActivityDifficulty(item.difficulty),
                        latest_score=(
                            latest_results[item.id].score
                            if item.id in latest_results
                            else None
                        ),
                    )
                )
                continue
            items.append(
                CompetencyMaterialDetail(
                    id=item.id,
                    title=item.title,
                    position=item.position,
                )
            )
        return tuple(items)

    @staticmethod
    def _has_later_released_competency(
        requested: CurriculumCompetencySnapshot,
        competencies: tuple[CurriculumCompetencySnapshot, ...],
        progress_by_competency: dict[str, CompetencyProgress],
    ) -> bool:
        return any(
            competency.position > requested.position
            and (
                progress_by_competency.get(competency.id) is not None
                and progress_by_competency[competency.id].content_released
            )
            for competency in competencies
        )

    @staticmethod
    def _recommend(
        competency: CurriculumCompetencySnapshot,
        progress: CompetencyProgress,
        items: tuple[CompetencyMaterialDetail | CompetencyActivityDetail, ...],
        learning_attempts: tuple[ActivityAttempt, ...],
        latest_results: dict[str, OfficialActivityResult],
    ) -> ActivityRecommendation | None:
        target_difficulty = GetCompetencyDetailUseCase._target_difficulty(
            GetCompetencyDetailUseCase._display_progress(progress)
        )
        activities = tuple(
            item
            for item in items
            if isinstance(item, CompetencyActivityDetail)
            and item.difficulty is target_difficulty
        )
        if not activities:
            return None

        previous_activity_id = (
            learning_attempts[-1].activity_id if learning_attempts else None
        )
        unevaluated = tuple(
            activity for activity in activities if activity.latest_score is None
        )
        if unevaluated:
            selected = GetCompetencyDetailUseCase._avoid_immediate_repeat(
                unevaluated,
                previous_activity_id,
            )
            recommendation_type = ActivityRecommendationType.NEW_ACTIVITY
        else:
            lowest_score = min(
                latest_results[activity.id].score for activity in activities
            )
            lowest_scored = tuple(
                activity
                for activity in activities
                if latest_results[activity.id].score == lowest_score
            )
            selected = GetCompetencyDetailUseCase._avoid_immediate_repeat(
                lowest_scored,
                previous_activity_id,
            )
            recommendation_type = ActivityRecommendationType.REINFORCEMENT

        return ActivityRecommendation(
            competency_id=competency.id,
            activity_id=selected.id,
            difficulty=selected.difficulty,
            type=recommendation_type,
        )

    @staticmethod
    def _avoid_immediate_repeat(
        candidates: tuple[CompetencyActivityDetail, ...],
        previous_activity_id: str | None,
    ) -> CompetencyActivityDetail:
        if not candidates:
            raise ValueError('Recommendation candidates cannot be empty.')
        if len(candidates) > 1 and previous_activity_id is not None:
            for candidate in candidates:
                if candidate.id != previous_activity_id:
                    return candidate
        return next(iter(candidates))

    @staticmethod
    def _target_difficulty(progress: Decimal) -> ActivityDifficulty:
        if progress < Decimal('40'):
            return ActivityDifficulty.EASY
        if progress < Decimal('70'):
            return ActivityDifficulty.MEDIUM
        return ActivityDifficulty.HARD
