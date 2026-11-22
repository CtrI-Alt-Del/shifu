from collections.abc import Mapping
from datetime import timedelta

from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    PracticePhoto,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
    PracticePhotoOwnerKind,
    PracticePhotoState,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures import (
    ChoiceEvaluationResult,
    ChoiceAttemptDetail,
    ChoiceResultDetail,
    MultipleSelectionAnswer,
    SingleChoiceAnswer,
    CodeAnswer,
    CodeSubmittedFile,
    CodeResultDetail,
    CodeRubricResult,
    OrderingAnswer,
    OrderingResultDetail,
    OrderingStepDetail,
    FillBlanksAnswer,
    FillBlanksEvaluationResult,
    FillBlanksExpectedBlank,
    FillBlanksResultDetail,
    PairMatchingAnswer,
    PairMatchingEvaluationResult,
    PairMatchingResultDetail,
    PairMatchingSelection,
    PracticalPreparationAnswer,
    PracticalPreparationResult,
    PracticalPreparationResultDetail,
    PracticalResultCriterionDetail,
    PracticalResultPhotoDetail,
    PracticalResultRecordDetail,
    PracticalUnassessableRecordDetail,
    TranslationAnswer,
    TranslationResultDetail,
    TranslationRubricResult,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.get_choice_activity_use_case import (
    GetChoiceActivityUseCase,
)
from shifu.shared.core.domain.errors import NotFoundError
from shifu.shared.core.domain.structures import (
    CurriculumChoicePartSnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumReactQuestionSnapshot,
    CurriculumHtmlCssJsQuestionSnapshot,
    CurriculumReactFastifyQuestionSnapshot,
    CurriculumCodeRubricPartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumOrderingQuestionSnapshot,
    CurriculumFillBlanksQuestionSnapshot,
    CurriculumPairMatchingQuestionSnapshot,
    CurriculumPracticalPreparationQuestionSnapshot,
    CurriculumTranslationQuestionSnapshot,
    CurriculumTranslationRubricPartSnapshot,
)
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider

type ResultDetail = (
    OrderingResultDetail
    | ChoiceResultDetail
    | CodeResultDetail
    | FillBlanksResultDetail
    | TranslationResultDetail
    | PairMatchingResultDetail
    | PracticalPreparationResultDetail
)


class GetChoiceAttemptUseCase:
    _TIMEOUT = timedelta(minutes=5)

    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        clock_provider: ClockProvider,
    ) -> None:
        self._learning_database = learning_database
        self._curriculum_content_provider = curriculum_content_provider
        self._clock_provider = clock_provider

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        attempt_id: str,
    ) -> ChoiceAttemptDetail:
        now = self._clock_provider.now()
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

            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            if (
                attempt is None
                or attempt.skill_experience_id != experience.id
                or attempt.competency_id != competency_id
                or attempt.activity_id != activity_id
                or attempt.kind is ActivityAttemptKind.DIAGNOSTIC
                or attempt.grading_snapshot is None
            ):
                raise NotFoundError

            evaluation = (
                repositories.activity_evaluations.find_by_attempt_id_for_update(
                    attempt.id
                )
            )
            if evaluation is None:
                raise NotFoundError

            if (
                evaluation.status is ActivityEvaluationStatus.PENDING
                and now >= evaluation.started_at + self._TIMEOUT
            ):
                evaluation.time_out('evaluation_timeout')
                repositories.activity_evaluations.update(evaluation)

            attempt_photos = (
                repositories.practice_photos.list_for_attempt(attempt.id)
                if any(
                    isinstance(item, CurriculumPracticalPreparationQuestionSnapshot)
                    for item in attempt.grading_snapshot.questions
                )
                else ()
            )
            if evaluation.status not in {
                ActivityEvaluationStatus.COMPLETED,
                ActivityEvaluationStatus.CLOSED_WITHOUT_GRADE,
            }:
                return ChoiceAttemptDetail(
                    attempt_id=attempt.id,
                    activity_id=attempt.activity_id,
                    status=evaluation.status,
                    submitted_at=attempt.submitted_at,
                    retry_allowed=evaluation.status is ActivityEvaluationStatus.FAILED,
                    failure_message=(
                        'A avaliação falhou. Você pode tentar novamente.'
                        if evaluation.status is ActivityEvaluationStatus.FAILED
                        else None
                    ),
                    questions=self._pending_question_details(attempt, attempt_photos),
                )

            all_attempts = (
                repositories.activity_attempts.find_many_by_skill_experience_id(
                    experience.id
                )
            )
            all_evaluations = (
                repositories.activity_evaluations.find_many_by_attempt_ids(
                    tuple(item.id for item in all_attempts)
                )
            )
            progress = repositories.competency_progresses.find_by_skill_experience_id_and_competency_id(
                experience.id, competency_id
            )
            is_mastered = (
                progress is not None
                and progress.status is CompetencyProgressStatus.MASTERED
            )
            disclosure = self._released_question_keys(
                attempt,
                all_attempts,
                all_evaluations,
                is_mastered,
                evaluation,
            )
            detail = self._result_detail(
                attempt, evaluation, disclosure, attempt_photos
            )
            completes_skill = self._completes_skill(
                attempt, experience.status, all_attempts
            )
            score = evaluation.score
            progress_before = evaluation.progress_before
            progress_after = evaluation.progress_after
            status_before = evaluation.status_before
            status_after = evaluation.status_after

        return ChoiceAttemptDetail(
            attempt_id=attempt.id,
            activity_id=attempt.activity_id,
            status=evaluation.status,
            submitted_at=attempt.submitted_at,
            retry_allowed=False,
            score=score,
            progress_before=progress_before,
            progress_after=progress_after,
            status_before=status_before,
            status_after=status_after,
            next_action=None,
            completes_skill=completes_skill,
            questions=detail,
        )

    @staticmethod
    def _completes_skill(
        attempt: ActivityAttempt,
        experience_status: SkillExperienceStatus,
        attempts: list[ActivityAttempt],
    ) -> bool:
        if (
            attempt.kind is not ActivityAttemptKind.LEARNING
            or experience_status is not SkillExperienceStatus.COMPLETED
        ):
            return False

        return not any(
            item.kind is ActivityAttemptKind.LEARNING
            and item.submitted_at > attempt.submitted_at
            for item in attempts
        )

    @staticmethod
    def _is_fully_correct(result: object) -> bool:
        if isinstance(result, ChoiceEvaluationResult | FillBlanksEvaluationResult):
            return result.is_correct

        return (
            isinstance(result, PairMatchingEvaluationResult)
            and result.outcome == 'full'
        )

    @staticmethod
    def _released_question_keys(
        current_attempt: ActivityAttempt,
        attempts: list[ActivityAttempt],
        evaluations: list[ActivityEvaluation],
        is_mastered: bool,
        current_evaluation: ActivityEvaluation,
    ) -> frozenset[str]:
        snapshot = current_attempt.grading_snapshot
        if snapshot is None:
            return frozenset()

        if is_mastered:
            return frozenset(question.key for question in snapshot.questions)

        evaluations_by_attempt = {item.attempt_id: item for item in evaluations}
        released: set[str] = {
            item.question_key
            for item in current_evaluation.parts
            if GetChoiceAttemptUseCase._is_fully_correct(item)
        }
        for later_attempt in attempts:
            if (
                later_attempt.activity_id != current_attempt.activity_id
                or later_attempt.competency_id != current_attempt.competency_id
                or later_attempt.submitted_at <= current_attempt.submitted_at
            ):
                continue

            later_evaluation = evaluations_by_attempt.get(later_attempt.id)
            if (
                later_evaluation is None
                or later_evaluation.status is not ActivityEvaluationStatus.COMPLETED
            ):
                continue

            released.update(
                item.question_key
                for item in later_evaluation.parts
                if GetChoiceAttemptUseCase._is_fully_correct(item)
            )
        return frozenset(released)

    @staticmethod
    def _result_detail(
        attempt: ActivityAttempt,
        evaluation: ActivityEvaluation,
        disclosed_keys: frozenset[str],
        photos: tuple[PracticePhoto, ...] = (),
    ) -> tuple[ResultDetail, ...]:
        snapshot = attempt.grading_snapshot
        if snapshot is None:
            raise NotFoundError

        answers = {answer.question_key: answer for answer in attempt.answers}
        results = GetChoiceAttemptUseCase._parts_of(evaluation, ChoiceEvaluationResult)
        code_results = GetChoiceAttemptUseCase._parts_of(evaluation, CodeRubricResult)
        translation_results = GetChoiceAttemptUseCase._parts_of(
            evaluation, TranslationRubricResult
        )
        pair_results = GetChoiceAttemptUseCase._parts_of(
            evaluation, PairMatchingEvaluationResult
        )
        practical_results = GetChoiceAttemptUseCase._parts_of(
            evaluation, PracticalPreparationResult
        )
        fill_blanks_details = GetChoiceAttemptUseCase._fill_blanks_details(
            snapshot.questions, answers, evaluation, disclosed_keys
        )
        details: list[ResultDetail] = []
        for question in snapshot.questions:
            answer = answers.get(question.key)
            detail: ResultDetail | None
            if isinstance(question, CurriculumFillBlanksQuestionSnapshot):
                details.extend(fill_blanks_details.get(question.key, ()))
                continue

            if isinstance(
                question,
                (
                    CurriculumJavascriptStdinQuestionSnapshot,
                    CurriculumReactQuestionSnapshot,
                    CurriculumHtmlCssJsQuestionSnapshot,
                    CurriculumReactFastifyQuestionSnapshot,
                ),
            ):
                detail = GetChoiceAttemptUseCase._code_result_detail(
                    question, answer, code_results.get(question.key), snapshot.parts
                )
            elif isinstance(question, CurriculumTranslationQuestionSnapshot):
                detail = GetChoiceAttemptUseCase._translation_result_detail(
                    question, answer, translation_results.get(question.key)
                )
            elif isinstance(question, CurriculumPracticalPreparationQuestionSnapshot):
                detail = GetChoiceAttemptUseCase._practical_result_detail(
                    question, answer, practical_results.get(question.key), photos
                )
            elif isinstance(question, CurriculumPairMatchingQuestionSnapshot):
                detail = GetChoiceAttemptUseCase._pair_result_detail(
                    question, answer, pair_results.get(question.key), disclosed_keys
                )
            elif isinstance(question, CurriculumOrderingQuestionSnapshot):
                ordering_result = results.get(question.key)
                detail = (
                    GetChoiceAttemptUseCase._ordering_result_detail(
                        question, answer, ordering_result, disclosed_keys
                    )
                    if ordering_result is not None
                    else None
                )
            else:
                detail = GetChoiceAttemptUseCase._choice_result_detail(
                    question, answer, results.get(question.key), disclosed_keys
                )
            if detail is not None:
                details.append(detail)
        return tuple(details)

    @staticmethod
    def _parts_of[PartT](
        evaluation: ActivityEvaluation, part_type: type[PartT]
    ) -> dict[str, PartT]:
        return {
            part.question_key: part
            for part in evaluation.parts
            if isinstance(part, part_type)
        }

    @staticmethod
    def _choice_result_detail(
        question: CurriculumChoiceQuestionSnapshot,
        answer: object | None,
        result: ChoiceEvaluationResult | None,
        disclosed_keys: frozenset[str],
    ) -> ChoiceResultDetail | None:
        if answer is None or result is None:
            return None

        if isinstance(answer, SingleChoiceAnswer):
            selected_keys = (answer.selected_option_key,)
        elif isinstance(answer, MultipleSelectionAnswer):
            selected_keys = answer.selected_option_keys
        else:
            return None
        return ChoiceResultDetail(
            question_key=question.key,
            prompt=question.prompt,
            selected_option_keys=selected_keys,
            score=result.score,
            is_correct=result.is_correct,
            explanation=result.explanation,
            disclosed_correct_option_keys=(
                tuple(option.key for option in question.options if option.is_correct)
                if question.key in disclosed_keys
                else ()
            ),
        )

    @staticmethod
    def _fill_blanks_details(
        questions: tuple[object, ...],
        answers: Mapping[str, object],
        evaluation: ActivityEvaluation,
        disclosed_keys: frozenset[str],
    ) -> dict[str, tuple[FillBlanksResultDetail, ...]]:
        results = {
            result.question_key: result
            for result in evaluation.parts
            if isinstance(result, FillBlanksEvaluationResult)
        }
        details: dict[str, tuple[FillBlanksResultDetail, ...]] = {}
        for question in questions:
            if not isinstance(question, CurriculumFillBlanksQuestionSnapshot):
                continue

            detail = GetChoiceAttemptUseCase._fill_blanks_result_detail(
                question,
                answers.get(question.key),
                results.get(question.key),
                question.key in disclosed_keys,
            )
            details[question.key] = () if detail is None else (detail,)
        return details

    @staticmethod
    def _fill_blanks_result_detail(
        question: CurriculumFillBlanksQuestionSnapshot,
        answer: object,
        result: FillBlanksEvaluationResult | None,
        disclosed: bool,
    ) -> FillBlanksResultDetail | None:
        if not isinstance(answer, FillBlanksAnswer) or result is None:
            return None

        public = GetChoiceActivityUseCase.fill_blanks_question_detail(question)
        return FillBlanksResultDetail(
            question_key=question.key,
            prompt=question.prompt,
            content_language=question.content_language,
            segments=public.segments,
            bank=public.bank,
            placements=answer.placements,
            score=result.score,
            is_correct=result.is_correct,
            correct_blank_count=len(result.correct_blank_keys),
            blank_count=result.blank_count,
            explanation=result.explanation,
            disclosed_expected_blanks=(
                tuple(
                    FillBlanksExpectedBlank(
                        blank_key=blank.key, accepted_words=blank.accepted_words
                    )
                    for blank in question.blanks
                )
                if disclosed
                else ()
            ),
        )

    @staticmethod
    def _code_result_detail(
        question: object,
        answer: object,
        result: CodeRubricResult | None,
        parts: tuple[
            CurriculumChoicePartSnapshot
            | CurriculumCodeRubricPartSnapshot
            | CurriculumTranslationRubricPartSnapshot,
            ...,
        ],
    ) -> CodeResultDetail | None:
        if (
            not isinstance(
                question,
                (
                    CurriculumJavascriptStdinQuestionSnapshot,
                    CurriculumReactQuestionSnapshot,
                    CurriculumHtmlCssJsQuestionSnapshot,
                    CurriculumReactFastifyQuestionSnapshot,
                ),
            )
            or not isinstance(answer, CodeAnswer)
            or result is None
        ):
            return None
        part = next((item for item in parts if item.question_key == question.key), None)
        if not isinstance(part, CurriculumCodeRubricPartSnapshot):
            return None
        project = {item.path: item.content for item in question.initial_files}
        project.update({item.path: item.content for item in answer.files})
        return CodeResultDetail(
            question_key=question.key,
            kind=question.kind,
            prompt=question.prompt,
            submitted_files=tuple(
                CodeSubmittedFile(path=path, content=content)
                for path, content in sorted(project.items())
            ),
            score=result.score,
            criterion_results=result.criterion_results,
            concept_observations=result.concept_observations,
        )

    @staticmethod
    def _ordering_result_detail(
        question: object,
        answer: object,
        result: ChoiceEvaluationResult,
        disclosed_keys: frozenset[str],
    ) -> OrderingResultDetail | None:
        if not isinstance(
            question, CurriculumOrderingQuestionSnapshot
        ) or not isinstance(answer, OrderingAnswer):
            return None
        return OrderingResultDetail(
            question_key=question.key,
            kind='ordering',
            prompt=question.prompt,
            steps=tuple(
                OrderingStepDetail(key=step.key, text=step.text)
                for step in question.steps
            ),
            submitted_step_keys=answer.ordered_step_keys,
            score=result.score,
            is_correct=result.is_correct,
            explanation=result.explanation,
            accepted_orders=(
                question.accepted_orders if question.key in disclosed_keys else ()
            ),
        )

    @staticmethod
    def _pair_result_detail(
        question: CurriculumPairMatchingQuestionSnapshot,
        answer: object | None,
        result: PairMatchingEvaluationResult | None,
        disclosed_keys: frozenset[str],
    ) -> PairMatchingResultDetail | None:
        if not isinstance(answer, PairMatchingAnswer) or result is None:
            return None

        return PairMatchingResultDetail(
            question_key=question.key,
            kind='pair_matching',
            prompt=question.prompt,
            submitted_pairs=answer.pairs,
            score=result.score,
            correct_pair_count=result.correct_pair_count,
            total_pair_count=result.total_pair_count,
            outcome=result.outcome,
            explanation=result.explanation,
            disclosed_correct_pairs=(
                tuple(
                    PairMatchingSelection(
                        word_key=pair.word_key,
                        translation_key=pair.translation_key,
                    )
                    for pair in question.correct_pairs
                )
                if question.key in disclosed_keys
                else ()
            ),
        )

    @staticmethod
    def _translation_result_detail(
        question: CurriculumTranslationQuestionSnapshot,
        answer: object | None,
        result: TranslationRubricResult | None,
    ) -> TranslationResultDetail | None:
        if not isinstance(answer, TranslationAnswer) or result is None:
            return None
        return TranslationResultDetail(
            question_key=question.key,
            kind=question.kind,
            prompt=question.prompt,
            submitted_text=answer.text,
            score=result.score,
            criterion_results=result.criterion_results,
            concept_observations=result.concept_observations,
        )

    @staticmethod
    def _practical_result_detail(
        question: CurriculumPracticalPreparationQuestionSnapshot,
        answer: object | None,
        result: PracticalPreparationResult | None,
        photos: tuple[PracticePhoto, ...],
    ) -> PracticalPreparationResultDetail | None:
        """Per-criterion weight, level and predefined comment, plus the frozen photos
        and reflection. Without a result the criteria carry no level yet."""
        if not isinstance(answer, PracticalPreparationAnswer):
            return None

        observed = (
            {item.criterion_key: item for item in result.criterion_results}
            if result is not None
            else {}
        )
        criteria: list[PracticalResultCriterionDetail] = []
        for criterion in question.criteria:
            item = observed.get(criterion.key)
            level = (
                next(
                    (
                        candidate
                        for candidate in criterion.levels
                        if candidate.comment_key == item.comment_key
                    ),
                    None,
                )
                if item is not None
                else None
            )
            criteria.append(
                PracticalResultCriterionDetail(
                    key=criterion.key,
                    name=criterion.name,
                    weight=criterion.weight,
                    level=item.level if item is not None else None,
                    comment=level.description if level is not None else None,
                )
            )
        closed = result is not None and result.closed_without_grade
        records = {record.key: record for record in question.records}
        unassessable = tuple(
            PracticalUnassessableRecordDetail(
                key=key,
                label=records[key].label,
                comment=' '.join(
                    dict.fromkeys(
                        rule.comment
                        for rule in question.insufficiency_rules
                        if rule.record_key == key
                    )
                ),
            )
            for key in (result.unassessable_record_keys if result is not None else ())
            if key in records
        )
        return PracticalPreparationResultDetail(
            question_key=question.key,
            prompt=question.prompt,
            records=tuple(
                PracticalResultRecordDetail(key=record.key, label=record.label)
                for record in question.records
            ),
            photos=tuple(
                PracticalResultPhotoDetail(
                    record_key=photo.record_key, photo_id=photo.id
                )
                for photo in photos
                if photo.owner_kind is PracticePhotoOwnerKind.ATTEMPT
                and photo.state is PracticePhotoState.READY
            ),
            reflection=answer.reflection,
            criteria=tuple(criteria),
            score=result.score if result is not None else None,
            closed_without_grade=closed,
            unassessable_records=unassessable,
            guidance=(
                ' '.join(dict.fromkeys(item.comment for item in unassessable))
                if closed and unassessable
                else None
            ),
        )

    @staticmethod
    def _pending_question_details(
        attempt: ActivityAttempt,
        photos: tuple[PracticePhoto, ...] = (),
    ) -> tuple[
        CodeResultDetail | TranslationResultDetail | PracticalPreparationResultDetail,
        ...,
    ]:
        snapshot = attempt.grading_snapshot
        if snapshot is None:
            return ()

        code_questions = {
            item.key: item
            for item in snapshot.questions
            if isinstance(
                item,
                (
                    CurriculumJavascriptStdinQuestionSnapshot,
                    CurriculumReactQuestionSnapshot,
                    CurriculumHtmlCssJsQuestionSnapshot,
                    CurriculumReactFastifyQuestionSnapshot,
                ),
            )
        }
        translation_questions = {
            item.key: item
            for item in snapshot.questions
            if isinstance(item, CurriculumTranslationQuestionSnapshot)
        }
        practical_questions = {
            item.key: item
            for item in snapshot.questions
            if isinstance(item, CurriculumPracticalPreparationQuestionSnapshot)
        }
        details: list[
            CodeResultDetail
            | TranslationResultDetail
            | PracticalPreparationResultDetail
        ] = []
        for answer in attempt.answers:
            if (
                isinstance(answer, PracticalPreparationAnswer)
                and answer.question_key in practical_questions
            ):
                practical = GetChoiceAttemptUseCase._practical_result_detail(
                    practical_questions[answer.question_key], answer, None, photos
                )
                if practical is not None:
                    details.append(practical)
            elif (
                isinstance(answer, CodeAnswer) and answer.question_key in code_questions
            ):
                question = code_questions[answer.question_key]
                project = {item.path: item.content for item in question.initial_files}
                project.update({item.path: item.content for item in answer.files})
                details.append(
                    CodeResultDetail(
                        question_key=question.key,
                        kind=question.kind,
                        prompt=question.prompt,
                        submitted_files=tuple(
                            CodeSubmittedFile(path=path, content=content)
                            for path, content in sorted(project.items())
                        ),
                        score=None,
                        criterion_results=(),
                        concept_observations=(),
                    )
                )
            elif (
                isinstance(answer, TranslationAnswer)
                and answer.question_key in translation_questions
            ):
                translation_question = translation_questions[answer.question_key]
                details.append(
                    TranslationResultDetail(
                        question_key=translation_question.key,
                        kind=translation_question.kind,
                        prompt=translation_question.prompt,
                        submitted_text=answer.text,
                        score=None,
                        criterion_results=(),
                        concept_observations=(),
                    )
                )
        return tuple(details)
