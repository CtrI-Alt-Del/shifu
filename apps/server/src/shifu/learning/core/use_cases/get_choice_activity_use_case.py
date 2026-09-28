from shifu.learning.core.domain.enums import ActivityDifficulty, SkillExperienceStatus
from shifu.learning.core.domain.structures import (
    ChoiceActivityDetail,
    ChoiceOptionDetail,
    ChoiceQuestionDetail,
    CodeQuestionDetail,
    CodeQuestionCriterionDetail,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.diagnostic_sequence import DiagnosticSequence
from shifu.learning.core.use_cases.choice_evidence_eligibility import (
    ChoiceEvidenceEligibility,
)
from shifu.shared.core.domain.errors import ConflictError, NotFoundError
from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumCodeRubricPartSnapshot,
)
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
        diagnostic_run_id: str | None = None,
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
            diagnostic = experience.status is SkillExperienceStatus.DIAGNOSING
            if diagnostic and (
                diagnostic_run_id is None
                or diagnostic_run_id != experience.diagnostic_run_id
            ):
                raise ConflictError
            if not diagnostic and not progress.content_released:
                raise NotFoundError

        if diagnostic:
            snapshot = self._curriculum_content_provider.get_diagnostic_activity(
                activity_id
            )
        else:
            mixed_getter = getattr(
                self._curriculum_content_provider, 'get_learning_activity', None
            )
            snapshot = mixed_getter(activity_id) if mixed_getter is not None else None
            if not isinstance(snapshot, CurriculumLearningActivitySnapshot) or not any(
                isinstance(item, CurriculumJavascriptStdinQuestionSnapshot)
                for item in snapshot.questions
            ):
                snapshot = self._curriculum_content_provider.get_choice_activity(
                    activity_id
                )
        if (
            snapshot is None
            or snapshot.id != activity_id
            or snapshot.competency_id != competency_id
            or snapshot.activity_type != ('diagnostic' if diagnostic else 'learning')
            or not self.is_eligible(snapshot, diagnostic=diagnostic)
        ):
            raise NotFoundError
        if isinstance(snapshot, CurriculumChoiceActivitySnapshot):
            live_catalog = self._curriculum_content_provider.get_skill_content(skill_id)
            if not ChoiceEvidenceEligibility.is_valid(snapshot, live_catalog):
                raise NotFoundError

        with self._learning_database.transaction() as repositories:
            if diagnostic:
                locked_experience = (
                    repositories.skill_experiences.find_by_id_for_update(experience.id)
                )
                if (
                    locked_experience is None
                    or locked_experience.status is not SkillExperienceStatus.DIAGNOSING
                    or locked_experience.diagnostic_run_id != diagnostic_run_id
                ):
                    raise ConflictError
                experience = locked_experience
                catalog = self._curriculum_content_provider.get_skill_content(skill_id)
                if catalog is None or not catalog.v2_eligible:
                    raise NotFoundError
                diagnostic_attempts = tuple(
                    repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id(
                        experience.id, diagnostic_run_id or ''
                    )
                )
                if diagnostic_attempts or not any(
                    item_competency_id == competency_id and item.id == activity_id
                    for item_competency_id, item in DiagnosticSequence.ordered(catalog)
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
            attempts = (
                [
                    item
                    for item in repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id(
                        experience.id, diagnostic_run_id or ''
                    )
                    if item.activity_id == activity_id
                ]
                if diagnostic
                else repositories.activity_attempts.find_many_by_skill_experience_id_and_activity_id(
                    experience.id, activity_id
                )
            )
            latest_attempt = attempts[-1] if attempts else None
            return ChoiceActivityDetail(
                activity_id=activity_id,
                title=snapshot.title,
                difficulty=ActivityDifficulty(snapshot.difficulty),
                questions=tuple(
                    CodeQuestionDetail(
                        key=question.key,
                        kind=question.kind,
                        prompt=question.prompt,
                        initial_files=question.initial_files,
                        entrypoint=question.entrypoint,
                        editable_paths=tuple(
                            item.path
                            for item in question.initial_files
                            if item.editable
                        ),
                        fixed_dependencies=question.fixed_dependencies,
                        permitted_commands=question.permitted_commands,
                        criteria=tuple(
                            CodeQuestionCriterionDetail(
                                key=item.key,
                                name=item.name,
                                weight_percentage=item.weight_percentage,
                            )
                            for part in (() if diagnostic else snapshot.parts)
                            if isinstance(part, CurriculumCodeRubricPartSnapshot)
                            and part.question_key == question.key
                            for item in part.criteria
                        ),
                    )
                    if isinstance(question, CurriculumJavascriptStdinQuestionSnapshot)
                    else ChoiceQuestionDetail(
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
                activity_revision=(
                    snapshot.diagnostic_revision if diagnostic else snapshot.revision
                ),
            )

    @staticmethod
    def is_eligible(
        snapshot: CurriculumChoiceActivitySnapshot | CurriculumLearningActivitySnapshot,
        *,
        diagnostic: bool = False,
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
