from shifu.learning.core.domain.enums import ActivityDifficulty, SkillExperienceStatus
from shifu.learning.core.domain.adaptive_learning_policy import AdaptiveLearningPolicy
from shifu.learning.core.domain.structures import (
    ChoiceActivityDetail,
    ChoiceOptionDetail,
    ChoiceQuestionDetail,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.diagnostic_sequence import DiagnosticSequence
from shifu.learning.core.use_cases.choice_evidence_eligibility import (
    ChoiceEvidenceEligibility,
)
from shifu.shared.core.domain.errors import NotFoundError
from shifu.shared.core.domain.structures import CurriculumChoiceActivitySnapshot
from shifu.shared.core.interfaces import CurriculumContentProvider


class GetChoiceActivityUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
    ) -> None:
        self._learning_database = learning_database
        self._curriculum_content_provider = curriculum_content_provider

    def execute(  # noqa: C901
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
    ) -> ChoiceActivityDetail:
        with self._learning_database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            if goal is None or goal.id != goal_id or goal.account_id != account_id:
                raise NotFoundError
            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if (
                experience is None
                or experience.goal_id != goal_id
                or experience.skill_id != skill_id
            ):
                raise NotFoundError
            progress = repositories.competency_progresses.find_by_skill_experience_id_and_competency_id(
                experience.id, competency_id
            )
            if (
                progress is None
                or progress.skill_experience_id != experience.id
                or progress.competency_id != competency_id
            ):
                raise NotFoundError
            diagnostic = (
                experience.policy_id == AdaptiveLearningPolicy.policy_id
                and experience.status is SkillExperienceStatus.DIAGNOSING
            )
            if not diagnostic and not progress.content_released:
                raise NotFoundError

        snapshot = self._curriculum_content_provider.get_choice_activity(activity_id)
        if (
            snapshot is None
            or snapshot.id != activity_id
            or snapshot.competency_id != competency_id
            or snapshot.activity_type != ('diagnostic' if diagnostic else 'learning')
            or not self._is_eligible(snapshot, diagnostic=diagnostic)
        ):
            raise NotFoundError
        if experience.policy_id == AdaptiveLearningPolicy.policy_id:
            live_catalog = self._curriculum_content_provider.get_skill_content(skill_id)
            if not ChoiceEvidenceEligibility.is_valid(snapshot, live_catalog):
                raise NotFoundError

        with self._learning_database.transaction() as repositories:
            if diagnostic:
                catalog = self._curriculum_content_provider.get_skill_content(skill_id)
                if catalog is None or not catalog.v2_eligible:
                    raise NotFoundError
                diagnostic_attempts = tuple(
                    repositories.activity_attempts.find_many_by_skill_experience_id(
                        experience.id
                    )
                )
                diagnostic_evaluations = tuple(
                    repositories.activity_evaluations.find_many_by_attempt_ids(
                        tuple(item.id for item in diagnostic_attempts)
                    )
                )
                next_item = DiagnosticSequence.next_item(
                    catalog, diagnostic_attempts, diagnostic_evaluations
                )
                if (
                    next_item is None
                    or next_item[0] != competency_id
                    or next_item[1].id != activity_id
                ):
                    raise NotFoundError
            unresolved = repositories.activity_evaluations.find_unresolved_by_skill_experience_id(
                experience.id
            )
            if unresolved is not None:
                unresolved_attempt = repositories.activity_attempts.find_by_id(
                    unresolved.attempt_id
                )
                if (
                    unresolved_attempt is not None
                    and unresolved_attempt.grading_snapshot is not None
                    and unresolved_attempt.grading_snapshot.id
                ):
                    unresolved_attempt_id = unresolved_attempt.id
                else:
                    unresolved_attempt_id = None
            else:
                unresolved_attempt_id = None
            attempts = repositories.activity_attempts.find_many_by_skill_experience_id_and_activity_id(
                experience.id, activity_id
            )
            latest_attempt = attempts[-1] if attempts else None
            return ChoiceActivityDetail(
                activity_id=activity_id,
                title=snapshot.title,
                difficulty=ActivityDifficulty(snapshot.difficulty),
                questions=tuple(
                    ChoiceQuestionDetail(
                        key=question.key,
                        kind=question.kind,
                        prompt=question.prompt,
                        options=tuple(
                            ChoiceOptionDetail(key=option.key, text=option.text)
                            for option in question.options
                        ),
                    )
                    for question in snapshot.questions
                ),
                can_submit=unresolved_attempt_id is None,
                latest_attempt_id=latest_attempt.id if latest_attempt else None,
                unresolved_attempt_id=unresolved_attempt_id,
                is_diagnostic=diagnostic,
            )

    @staticmethod
    def _is_eligible(
        snapshot: CurriculumChoiceActivitySnapshot, *, diagnostic: bool = False
    ) -> bool:
        question_keys = tuple(question.key for question in snapshot.questions)
        part_keys = tuple(part.question_key for part in snapshot.parts)
        return (
            (
                bool(snapshot.questions)
                if diagnostic
                else 3 <= len(snapshot.questions) <= 5
            )
            and len(set(question_keys)) == len(question_keys)
            and len(part_keys) == len(question_keys)
            and set(part_keys) == set(question_keys)
            and sum(part.weight_percentage for part in snapshot.parts) == 100
        )
