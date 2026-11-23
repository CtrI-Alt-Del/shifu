from shifu.learning.core.use_cases.mixed_question_snapshots import (
    MixedQuestionSnapshots,
)
from datetime import UTC

from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    PracticeDraft,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    PracticePhotoState,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.errors import (
    PracticeDraftConflictError,
    PracticeDraftIncompleteError,
)
from shifu.learning.core.domain.structures import (
    ActivityAnswer,
    ChoiceAnswerSubmission,
    ChoiceAttemptDetail,
    MultipleSelectionAnswer,
    OrderingAnswer,
    OrderingAnswerSubmission,
    SingleChoiceAnswer,
    ChoiceSubmissionOutcome,
    CodeAnswer,
    FillBlanksAnswer,
    PairMatchingAnswer,
    PracticalPreparationAnswer,
    PracticalPreparationAnswerSubmission,
    TranslationAnswer,
)
from shifu.learning.core.domain.events.activity_submission_requested_event import (
    ActivitySubmissionRequestedEvent,
    ActivitySubmissionRequestedPayload,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.choice_evidence_eligibility import (
    ChoiceEvidenceEligibility,
)
from shifu.learning.core.use_cases.code_answer_validation import (
    CodeAnswerValidation,
)
from shifu.learning.core.use_cases.fill_blanks_scoring import FillBlanksScoring
from shifu.learning.core.use_cases.pair_matching_scoring import PairMatchingScoring
from shifu.shared.core.domain.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumReactQuestionSnapshot,
    CurriculumHtmlCssJsQuestionSnapshot,
    CurriculumPairMatchingQuestionSnapshot,
    CurriculumReactFastifyQuestionSnapshot,
    CurriculumOrderingQuestionSnapshot,
    CurriculumFillBlanksQuestionSnapshot,
    CurriculumImageChoiceQuestionSnapshot,
    CurriculumPracticalPreparationQuestionSnapshot,
    CurriculumTranslationQuestionSnapshot,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)
from shifu.learning.core.use_cases.ordering_answer_validation import (
    OrderingAnswerValidation,
)


type SubmittedAnswer = (
    ChoiceAnswerSubmission
    | CodeAnswer
    | OrderingAnswerSubmission
    | FillBlanksAnswer
    | TranslationAnswer
    | PairMatchingAnswer
    | PracticalPreparationAnswerSubmission
)


class SubmitChoiceActivityUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        clock_provider: ClockProvider,
        identifier_provider: IdentifierProvider,
        max_code_assessment_input_bytes: int = CodeAnswerValidation.MAX_ASSESSMENT_INPUT_BYTES,
    ) -> None:
        self._learning_database = learning_database
        self._curriculum_content_provider = curriculum_content_provider
        self._clock_provider = clock_provider
        self._identifier_provider = identifier_provider
        self._max_code_assessment_input_bytes = max_code_assessment_input_bytes

    def execute(  # noqa: C901
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        submission_key: str,
        answers: tuple[SubmittedAnswer, ...],
        activity_revision: str | None = None,
        diagnostic_run_id: str | None = None,
        time_zone: str | None = None,
        passage_key: str | None = None,
    ) -> ChoiceSubmissionOutcome:
        if not submission_key.strip():
            raise ValidationError

        with self._learning_database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if goal is None or goal.account_id != account_id or experience is None:
                raise NotFoundError

            if experience.status is SkillExperienceStatus.DIAGNOSING:
                raise ConflictError

            experience_id = experience.id
            existing = repositories.activity_attempts.find_by_skill_experience_id_and_submission_key(
                experience_id, submission_key
            )
            if existing is not None:
                if existing.kind is ActivityAttemptKind.DIAGNOSTIC:
                    raise ConflictError

                return self._replayed_outcome(
                    repositories, existing, competency_id, activity_id, answers
                )

            active_ordering_passage = repositories.ordering_passages.find_active(
                experience_id, activity_id
            )
            if (
                active_ordering_passage is not None
                and active_ordering_passage.passage_key != passage_key
            ):
                raise ConflictError

        if active_ordering_passage is not None:
            snapshot = active_ordering_passage.grading_snapshot
        else:
            mixed_getter = getattr(
                self._curriculum_content_provider, 'get_learning_activity', None
            )
            snapshot = mixed_getter(activity_id) if mixed_getter is not None else None
            if not isinstance(
                snapshot, CurriculumLearningActivitySnapshot
            ) or not MixedQuestionSnapshots.has_non_choice(snapshot.questions):
                snapshot = self._curriculum_content_provider.get_choice_activity(
                    activity_id
                )

        if (
            snapshot is None
            or snapshot.id != activity_id
            or snapshot.competency_id != competency_id
        ):
            raise NotFoundError

        if snapshot.activity_type == 'diagnostic':
            raise ConflictError

        if (
            isinstance(snapshot, CurriculumLearningActivitySnapshot)
            and snapshot.revision != activity_revision
        ):
            raise ConflictError

        has_ordering = isinstance(snapshot, CurriculumLearningActivitySnapshot) and any(
            isinstance(item, CurriculumOrderingQuestionSnapshot)
            for item in snapshot.questions
        )
        if has_ordering != (passage_key is not None):
            raise ConflictError
        normalized_answers = self.normalize_answers(
            snapshot, answers, self._max_code_assessment_input_bytes
        )
        v2_catalog = self._curriculum_content_provider.get_skill_content(skill_id)

        now = self._clock_provider.now()
        with self._learning_database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            experience = repositories.skill_experiences.find_by_id_for_update(
                experience_id
            )
            progress = repositories.competency_progresses.find_by_skill_experience_id_and_competency_id(
                experience_id, competency_id
            )
            if (
                goal is None
                or goal.account_id != account_id
                or experience is None
                or experience.goal_id != goal_id
                or experience.skill_id != skill_id
                or progress is None
            ):
                raise NotFoundError

            if experience.status is SkillExperienceStatus.DIAGNOSING:
                raise ConflictError

            existing = repositories.activity_attempts.find_by_skill_experience_id_and_submission_key(
                experience_id, submission_key
            )
            if existing is not None:
                if existing.kind is ActivityAttemptKind.DIAGNOSTIC and (
                    diagnostic_run_id is None
                    or existing.diagnostic_run_id != diagnostic_run_id
                    or experience.diagnostic_run_id != diagnostic_run_id
                ):
                    raise ConflictError

                return self._replayed_outcome(
                    repositories, existing, competency_id, activity_id, answers
                )

            ordering_passage = repositories.ordering_passages.find_active(
                experience_id, activity_id
            )
            if has_ordering:
                if (
                    ordering_passage is None
                    or ordering_passage.passage_key != passage_key
                    or ordering_passage.activity_revision != snapshot.revision
                ):
                    raise ConflictError
                for ordering in (
                    item
                    for item in normalized_answers
                    if isinstance(item, OrderingAnswer)
                ):
                    verified = next(
                        (
                            item
                            for item in ordering_passage.verified_orderings
                            if item.question_key == ordering.question_key
                        ),
                        None,
                    )
                    if (
                        verified is None
                        or verified.ordered_step_keys != ordering.ordered_step_keys
                    ):
                        raise ConflictError
            elif passage_key is not None:
                raise ConflictError

            if isinstance(
                snapshot, CurriculumChoiceActivitySnapshot
            ) and not ChoiceEvidenceEligibility.is_valid(snapshot, v2_catalog):
                raise NotFoundError

            if snapshot.activity_type != 'learning' or not progress.content_released:
                raise NotFoundError

            if experience.status not in {
                SkillExperienceStatus.LEARNING,
                SkillExperienceStatus.COMPLETED,
            }:
                raise NotFoundError

            kind = (
                ActivityAttemptKind.REVIEW
                if experience.status is SkillExperienceStatus.COMPLETED
                else ActivityAttemptKind.LEARNING
            )

            unresolved = repositories.activity_evaluations.find_unresolved_by_skill_experience_id(
                experience_id
            )
            if unresolved is not None:
                raise ConflictError

            practice_draft = self._confirm_practice_draft(
                repositories, experience_id, activity_id, snapshot, normalized_answers
            )
            frozen_answers = (
                self._freeze_practice_reflection(
                    normalized_answers, practice_draft.reflection
                )
                if practice_draft is not None
                else normalized_answers
            )
            attempt_id = self._identifier_provider.generate()
            evaluation_id = self._identifier_provider.generate()
            run_id = self._identifier_provider.generate()
            attempt = ActivityAttempt.create(
                id=attempt_id,
                skill_experience_id=experience_id,
                competency_id=competency_id,
                activity_id=activity_id,
                kind=kind,
                answers=frozen_answers,
                submitted_at=now,
                submission_key=submission_key,
                grading_snapshot=snapshot,
                diagnostic_run_id=None,
                time_zone=time_zone,
            )
            evaluation = ActivityEvaluation.create(
                id=evaluation_id,
                attempt_id=attempt_id,
                status=ActivityEvaluationStatus.PENDING,
                parts=(),
                started_at=now,
                run_id=run_id,
            )
            repositories.activity_attempts.add(attempt)
            repositories.activity_evaluations.add(evaluation)
            repositories.events.add(
                ActivitySubmissionRequestedEvent(
                    payload=ActivitySubmissionRequestedPayload(
                        attempt_id=attempt_id,
                        run_id=run_id,
                        skill_experience_id=experience_id,
                        activity_id=activity_id,
                        kind=kind,
                        requested_at=now.astimezone(UTC)
                        .isoformat()
                        .replace('+00:00', 'Z'),
                    )
                )
            )
            if ordering_passage is not None:
                ordering_passage.consume()
                repositories.ordering_passages.update(ordering_passage)
            if practice_draft is not None:
                repositories.practice_photos.reassign_to_attempt(
                    practice_draft.id, attempt_id
                )
                practice_draft.consume()
                repositories.practice_drafts.update(practice_draft)
            return ChoiceSubmissionOutcome(
                attempt=ChoiceAttemptDetail(
                    attempt_id=attempt_id,
                    activity_id=activity_id,
                    status=ActivityEvaluationStatus.PENDING,
                    submitted_at=now,
                    retry_allowed=False,
                ),
                replayed=False,
                is_diagnostic=False,
            )

    def _replayed_outcome(
        self,
        repositories: LearningDatabaseRepositories,
        existing: ActivityAttempt,
        competency_id: str,
        activity_id: str,
        answers: tuple[SubmittedAnswer, ...],
    ) -> ChoiceSubmissionOutcome:
        snapshot = existing.grading_snapshot
        if (
            snapshot is None
            or existing.activity_id != activity_id
            or existing.competency_id != competency_id
            or not self._same_answers(
                existing.answers,
                self.normalize_answers(
                    snapshot, answers, self._max_code_assessment_input_bytes
                ),
            )
        ):
            raise ConflictError

        evaluation = repositories.activity_evaluations.find_by_attempt_id(existing.id)
        if evaluation is None:
            raise ConflictError

        return ChoiceSubmissionOutcome(
            attempt=ChoiceAttemptDetail(
                attempt_id=existing.id,
                activity_id=existing.activity_id,
                status=evaluation.status,
                submitted_at=existing.submitted_at,
                retry_allowed=evaluation.status is ActivityEvaluationStatus.FAILED,
            ),
            replayed=True,
            is_diagnostic=existing.kind is ActivityAttemptKind.DIAGNOSTIC,
        )

    @staticmethod
    def _same_answers(
        existing: tuple[ActivityAnswer, ...], submitted: tuple[ActivityAnswer, ...]
    ) -> bool:
        """A practical answer replays by its confirmed draft revision; the reflection
        was frozen from the draft and is not part of the client's request."""
        if len(existing) != len(submitted):
            return False

        return all(
            (
                stored.question_key == sent.question_key
                and stored.draft_revision == sent.draft_revision
            )
            if isinstance(stored, PracticalPreparationAnswer)
            and isinstance(sent, PracticalPreparationAnswer)
            else stored == sent
            for stored, sent in zip(existing, submitted, strict=True)
        )

    @staticmethod
    def _freeze_practice_reflection(
        answers: tuple[ActivityAnswer, ...], reflection: str
    ) -> tuple[ActivityAnswer, ...]:
        return tuple(
            PracticalPreparationAnswer(
                question_key=answer.question_key,
                draft_revision=answer.draft_revision,
                reflection=reflection,
            )
            if isinstance(answer, PracticalPreparationAnswer)
            else answer
            for answer in answers
        )

    @staticmethod
    def _confirm_practice_draft(
        repositories: LearningDatabaseRepositories,
        experience_id: str,
        activity_id: str,
        snapshot: CurriculumChoiceActivitySnapshot | CurriculumLearningActivitySnapshot,
        answers: tuple[ActivityAnswer, ...],
    ) -> PracticeDraft | None:
        """Lock the draft and refuse the submit unless it is the revision the client saw,
        with a ready photo for every record and none still uploading."""
        answer = next(
            (item for item in answers if isinstance(item, PracticalPreparationAnswer)),
            None,
        )
        question = next(
            (
                item
                for item in snapshot.questions
                if isinstance(item, CurriculumPracticalPreparationQuestionSnapshot)
            ),
            None,
        )
        if answer is None or question is None:
            return None

        draft = repositories.practice_drafts.find_active_for_update(
            experience_id, activity_id
        )
        if draft is None or draft.revision != answer.draft_revision:
            raise PracticeDraftConflictError

        photos = repositories.practice_photos.list_live_for_draft(draft.id)
        if any(photo.state is PracticePhotoState.UPLOADING for photo in photos):
            raise PracticeDraftIncompleteError

        ready_records = {
            photo.record_key
            for photo in photos
            if photo.state is PracticePhotoState.READY
        }
        if ready_records != {record.key for record in question.records}:
            raise PracticeDraftIncompleteError

        return draft

    @staticmethod
    def normalize_answers(  # noqa: C901
        snapshot: CurriculumChoiceActivitySnapshot | CurriculumLearningActivitySnapshot,
        answers: tuple[SubmittedAnswer, ...],
        max_bytes: int = CodeAnswerValidation.MAX_ASSESSMENT_INPUT_BYTES,
    ) -> tuple[ActivityAnswer, ...]:
        if len(answers) != len(snapshot.questions):
            raise ValidationError

        normalized: list[ActivityAnswer] = []
        for question, answer in zip(snapshot.questions, answers, strict=True):
            if answer.question_key != question.key:
                raise ValidationError

            if isinstance(
                question,
                (
                    CurriculumJavascriptStdinQuestionSnapshot,
                    CurriculumReactQuestionSnapshot,
                    CurriculumHtmlCssJsQuestionSnapshot,
                    CurriculumReactFastifyQuestionSnapshot,
                ),
            ):
                if not isinstance(answer, CodeAnswer):
                    raise ValidationError
                normalized.append(
                    CodeAnswerValidation.normalize(question, answer, max_bytes)
                )
                continue

            if isinstance(question, CurriculumOrderingQuestionSnapshot):
                if not isinstance(answer, OrderingAnswerSubmission):
                    raise ValidationError
                OrderingAnswerValidation.validate(question, answer.ordered_step_keys)
                normalized.append(
                    OrderingAnswer(
                        question_key=answer.question_key,
                        ordered_step_keys=answer.ordered_step_keys,
                    )
                )
                continue

            if isinstance(question, CurriculumFillBlanksQuestionSnapshot):
                if not isinstance(answer, FillBlanksAnswer):
                    raise ValidationError

                normalized.append(FillBlanksScoring.normalize(question, answer))
                continue
            if isinstance(question, CurriculumPracticalPreparationQuestionSnapshot):
                if (
                    not isinstance(answer, PracticalPreparationAnswerSubmission)
                    or answer.draft_revision < 0
                ):
                    raise ValidationError
                normalized.append(
                    PracticalPreparationAnswer(
                        question_key=answer.question_key,
                        draft_revision=answer.draft_revision,
                        reflection='',
                    )
                )
                continue

            if isinstance(question, CurriculumTranslationQuestionSnapshot):
                if not isinstance(answer, TranslationAnswer):
                    raise ValidationError
                normalized.append(
                    TranslationAnswer(
                        question_key=answer.question_key, text=answer.text
                    )
                )
                continue

            if isinstance(question, CurriculumPairMatchingQuestionSnapshot):
                if not isinstance(answer, PairMatchingAnswer):
                    raise ValidationError
                PairMatchingScoring.validate(question, answer)
                normalized.append(
                    PairMatchingAnswer(
                        question_key=answer.question_key,
                        pairs=tuple(
                            sorted(answer.pairs, key=lambda pair: pair.word_key)
                        ),
                    )
                )
                continue

            if not isinstance(answer, ChoiceAnswerSubmission):
                raise ValidationError

            if isinstance(question, CurriculumImageChoiceQuestionSnapshot):
                selected_keys = answer.selected_option_keys
                if len(selected_keys) != 1 or selected_keys[0] not in {
                    option.key for option in question.options
                }:
                    raise ValidationError

                normalized.append(
                    SingleChoiceAnswer(
                        question_key=answer.question_key,
                        selected_option_key=selected_keys[0],
                    )
                )
                continue

            option_keys = {option.key for option in question.options}
            selected = answer.selected_option_keys
            if not selected or len(set(selected)) != len(selected):
                raise ValidationError

            if not set(selected).issubset(option_keys):
                raise ValidationError

            if question.kind == 'single_choice':
                if len(selected) != 1:
                    raise ValidationError

                normalized.append(
                    SingleChoiceAnswer(
                        question_key=answer.question_key,
                        selected_option_key=selected[0],
                    )
                )
            else:
                normalized.append(
                    MultipleSelectionAnswer(
                        question_key=answer.question_key,
                        selected_option_keys=selected,
                    )
                )
        return tuple(normalized)
