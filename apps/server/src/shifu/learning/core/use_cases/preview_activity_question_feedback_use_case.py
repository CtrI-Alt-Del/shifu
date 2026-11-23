from decimal import Decimal

from shifu.learning.core.domain.entities import OrderingPassage
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.structures import (
    ChoiceAnswerSubmission,
    OrderingAnswerSubmission,
    VerifiedOrdering,
    CodeAnswer,
    CodeSubmittedFile,
    CodeCriterionResult,
    CodeConceptObservationResult,
    FillBlanksAnswer,
    PairMatchingAnswer,
    PairMatchingSelection,
    TranslationAnswer,
)
from shifu.learning.core.use_cases.get_choice_activity_use_case import (
    GetChoiceActivityUseCase,
)
from shifu.learning.core.use_cases.fill_blanks_scoring import FillBlanksScoring
from shifu.learning.core.use_cases.pair_matching_scoring import PairMatchingScoring
from shifu.learning.core.use_cases.code_answer_validation import (
    CodeAnswerValidation,
    CodeQuestionSnapshot,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.ordering_answer_validation import (
    OrderingAnswerValidation,
)
from shifu.shared.core.domain.errors import (
    ConflictError,
    ServiceUnavailableError,
    ValidationError,
)
from shifu.shared.core.domain.structures import (
    CodeRubricAssessmentInput,
    CodeRubricDecisions,
    CurriculumChoicePartSnapshot,
    CurriculumCodeConceptCriterionSnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumReactQuestionSnapshot,
    CurriculumHtmlCssJsQuestionSnapshot,
    CurriculumReactFastifyQuestionSnapshot,
    CurriculumCodeRubricPartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumImageChoiceQuestionSnapshot,
    CurriculumOrderingQuestionSnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumFillBlanksQuestionSnapshot,
    CurriculumPairMatchingQuestionSnapshot,
    CurriculumTranslationQuestionSnapshot,
    CurriculumTranslationRubricPartSnapshot,
    TranslationRubricAssessmentInput,
)
from shifu.shared.core.interfaces import (
    CodeRubricAssessorProvider,
    CurriculumContentProvider,
    IdentifierProvider,
    TranslationRubricAssessorProvider,
)
from shifu.shared.core.domain.structures import structure


@structure
class PreliminaryQuestionResult:
    status: str
    score: Decimal | None
    explanation: str | None = None
    is_correct: bool | None = None
    criteria: tuple[CodeCriterionResult, ...] = ()
    concept_observations: tuple[CodeConceptObservationResult, ...] = ()
    submitted_files: tuple[CodeSubmittedFile, ...] = ()
    correct_blank_count: int | None = None
    blank_count: int | None = None
    submitted_text: str | None = None
    submitted_pairs: tuple[PairMatchingSelection, ...] | None = None
    correct_pair_count: int | None = None
    total_pair_count: int | None = None
    outcome: str | None = None
    option_feedback: str | None = None


type PreviewAnswer = (
    OrderingAnswerSubmission
    | ChoiceAnswerSubmission
    | CodeAnswer
    | FillBlanksAnswer
    | TranslationAnswer
    | PairMatchingAnswer
)


class PreviewActivityQuestionFeedbackUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        code_rubric_assessor_provider: CodeRubricAssessorProvider,
        translation_rubric_assessor_provider: TranslationRubricAssessorProvider,
        max_code_assessment_input_bytes: int = 262144,
        identifier_provider: IdentifierProvider | None = None,
    ) -> None:
        self._learning_database = learning_database
        self._curriculum_content_provider = curriculum_content_provider
        self._code_rubric_assessor_provider = code_rubric_assessor_provider
        self._translation_rubric_assessor_provider = (
            translation_rubric_assessor_provider
        )
        self._max_code_assessment_input_bytes = max_code_assessment_input_bytes
        self._identifier_provider = identifier_provider

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        question_key: str,
        activity_revision: str,
        answer: PreviewAnswer,
        passage_key: str | None = None,
    ) -> PreliminaryQuestionResult:
        detail = GetChoiceActivityUseCase(
            self._learning_database, self._curriculum_content_provider
        ).execute(account_id, goal_id, skill_id, competency_id, activity_id)
        self._assert_revision(detail.activity_revision, activity_revision)
        self._assert_question_key(answer.question_key, question_key)

        if isinstance(answer, OrderingAnswerSubmission):
            return self._verify_ordering(
                account_id,
                goal_id,
                skill_id,
                competency_id,
                activity_id,
                activity_revision,
                passage_key,
                answer,
            )

        snapshot = self._preview_snapshot(
            goal_id, skill_id, activity_id, detail.ordering_passage_key
        )
        if snapshot is None:
            raise ConflictError
        self._assert_revision(snapshot.revision, activity_revision)

        question = next(
            (item for item in snapshot.questions if item.key == question_key), None
        )
        if question is None:
            raise ValidationError

        if isinstance(
            question,
            (
                CurriculumFillBlanksQuestionSnapshot,
                CurriculumPairMatchingQuestionSnapshot,
            ),
        ):
            return self._execute_deterministic(question, answer)

        if isinstance(
            question,
            (
                CurriculumJavascriptStdinQuestionSnapshot,
                CurriculumReactQuestionSnapshot,
                CurriculumHtmlCssJsQuestionSnapshot,
                CurriculumReactFastifyQuestionSnapshot,
            ),
        ):
            return self._execute_code(question, answer, snapshot.parts)

        if isinstance(question, CurriculumTranslationQuestionSnapshot):
            return self._execute_translation(question, answer, snapshot.parts)

        return self._choice_result(question, answer)

    def _preview_snapshot(
        self,
        goal_id: str,
        skill_id: str,
        activity_id: str,
        passage_key: str | None,
    ) -> CurriculumLearningActivitySnapshot | None:
        if passage_key is None:
            return self._curriculum_content_provider.get_learning_activity(activity_id)

        with self._learning_database.transaction() as repositories:
            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if (
                experience is None
                or experience.goal_id != goal_id
                or experience.skill_id != skill_id
            ):
                raise ConflictError

            passage = repositories.ordering_passages.find_active(
                experience.id, activity_id
            )
            if (
                passage is None
                or passage.skill_experience_id != experience.id
                or passage.activity_id != activity_id
                or passage.passage_key != passage_key
                or passage.status != 'active'
            ):
                raise ConflictError

            return passage.grading_snapshot

    @staticmethod
    def _choice_result(
        question: object,
        answer: PreviewAnswer,
    ) -> PreliminaryQuestionResult:
        if not isinstance(answer, ChoiceAnswerSubmission):
            raise ValidationError

        if isinstance(question, CurriculumImageChoiceQuestionSnapshot):
            return PreviewActivityQuestionFeedbackUseCase._image_choice_result(
                question, answer
            )

        if not isinstance(question, CurriculumChoiceQuestionSnapshot):
            raise ValidationError

        selected = answer.selected_option_keys
        option_keys = {item.key for item in question.options}
        if (
            not selected
            or len(selected) != len(set(selected))
            or not set(selected) <= option_keys
            or (question.kind == 'single_choice' and len(selected) != 1)
        ):
            raise ValidationError

        correct = selected and set(selected) == {
            item.key for item in question.options if item.is_correct
        }
        return PreliminaryQuestionResult(
            status='conclusive',
            score=Decimal(100 if correct else 0),
            is_correct=bool(correct),
            explanation=question.correct_explanation
            if correct
            else question.incorrect_explanation,
        )

    @staticmethod
    def _image_choice_result(
        question: CurriculumImageChoiceQuestionSnapshot,
        answer: ChoiceAnswerSubmission,
    ) -> PreliminaryQuestionResult:
        selected = next(
            (
                option
                for option in question.options
                if option.key in answer.selected_option_keys
            ),
            None,
        )
        if len(answer.selected_option_keys) != 1 or selected is None:
            raise ValidationError

        return PreliminaryQuestionResult(
            status='conclusive',
            score=Decimal(100 if selected.is_correct else 0),
            is_correct=selected.is_correct,
            explanation=question.correct_explanation
            if selected.is_correct
            else question.incorrect_explanation,
            option_feedback=selected.feedback,
        )

    @staticmethod
    def _execute_deterministic(
        question: CurriculumFillBlanksQuestionSnapshot
        | CurriculumPairMatchingQuestionSnapshot,
        answer: PreviewAnswer,
    ) -> PreliminaryQuestionResult:
        if isinstance(question, CurriculumFillBlanksQuestionSnapshot):
            return PreviewActivityQuestionFeedbackUseCase.fill_blanks_result(
                question, answer
            )

        return PreviewActivityQuestionFeedbackUseCase.pair_matching_result(
            question, answer
        )

    def _execute_code(
        self,
        question: CurriculumJavascriptStdinQuestionSnapshot
        | CurriculumReactQuestionSnapshot
        | CurriculumHtmlCssJsQuestionSnapshot
        | CurriculumReactFastifyQuestionSnapshot,
        answer: PreviewAnswer,
        parts: tuple[
            CurriculumChoicePartSnapshot
            | CurriculumCodeRubricPartSnapshot
            | CurriculumTranslationRubricPartSnapshot,
            ...,
        ],
    ) -> PreliminaryQuestionResult:
        if not isinstance(answer, CodeAnswer):
            raise ValidationError

        part = next((item for item in parts if item.question_key == question.key), None)
        if not isinstance(part, CurriculumCodeRubricPartSnapshot):
            raise ValidationError

        request = self.build_code_assessment_input(
            question, part, answer, self._max_code_assessment_input_bytes
        )
        decisions = self._code_rubric_assessor_provider.assess(request)
        return self.code_result(
            question,
            part,
            answer,
            decisions,
            self._max_code_assessment_input_bytes,
        )

    def _execute_translation(
        self,
        question: CurriculumTranslationQuestionSnapshot,
        answer: PreviewAnswer,
        parts: tuple[
            CurriculumChoicePartSnapshot
            | CurriculumCodeRubricPartSnapshot
            | CurriculumTranslationRubricPartSnapshot,
            ...,
        ],
    ) -> PreliminaryQuestionResult:
        if not isinstance(answer, TranslationAnswer):
            raise ValidationError

        part = next((item for item in parts if item.question_key == question.key), None)
        if not isinstance(part, CurriculumTranslationRubricPartSnapshot):
            raise ValidationError

        request = TranslationRubricAssessmentInput(
            question_kind=question.kind,
            source_text=question.source_text,
            source_language=question.source_language,
            target_language=question.target_language,
            reference_translations=question.reference_translations,
            submitted_text=answer.text,
            rubric_criteria=part.criteria,
            concept_criteria=question.concept_criteria,
        )
        decisions = self._translation_rubric_assessor_provider.assess(request)
        return self.translation_result(question, part, answer, decisions)

    @staticmethod
    def _assert_revision(actual: str | None, expected: str) -> None:
        if actual != expected:
            raise ConflictError

    @staticmethod
    def _assert_question_key(actual: str, expected: str) -> None:
        if actual != expected:
            raise ValidationError

    def _verify_ordering(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        activity_revision: str,
        passage_key: str | None,
        answer: OrderingAnswerSubmission,
    ) -> PreliminaryQuestionResult:
        if not passage_key or self._identifier_provider is None:
            raise ValidationError

        with self._learning_database.transaction() as repositories:
            experience_id, active, snapshot = self._ordering_context(
                repositories,
                account_id,
                goal_id,
                skill_id,
                competency_id,
                activity_id,
                activity_revision,
                passage_key,
            )

            question = next(
                (
                    item
                    for item in snapshot.questions
                    if item.key == answer.question_key
                ),
                None,
            )
            if not isinstance(question, CurriculumOrderingQuestionSnapshot):
                raise ValidationError

            verified = OrderingAnswerValidation.verify(
                question, answer.ordered_step_keys
            )
            previous = self._previous_ordering(active, answer)
            if previous is not None:
                return self._ordering_result(previous)

            if active is None:
                active = OrderingPassage.create(
                    id=self._identifier_provider.generate(),
                    skill_experience_id=experience_id,
                    activity_id=activity_id,
                    passage_key=passage_key,
                    activity_revision=activity_revision,
                    grading_snapshot=snapshot,
                )
                active.add_verified(verified)
                repositories.ordering_passages.add(active)
            else:
                active.add_verified(verified)
                repositories.ordering_passages.update(active)
            return self._ordering_result(verified)

    def _ordering_context(
        self,
        repositories: LearningDatabaseRepositories,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        activity_revision: str,
        passage_key: str,
    ) -> tuple[str, OrderingPassage | None, CurriculumLearningActivitySnapshot]:
        goal = repositories.goals.find_by_id(goal_id)
        experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
            goal_id, skill_id
        )
        if (
            goal is None
            or goal.account_id != account_id
            or experience is None
            or experience.goal_id != goal_id
            or experience.skill_id != skill_id
        ):
            raise ConflictError

        experience = repositories.skill_experiences.find_by_id_for_update(experience.id)
        if experience is None:
            raise ConflictError

        progress = repositories.competency_progresses.find_by_skill_experience_id_and_competency_id(
            experience.id, competency_id
        )
        unresolved = (
            repositories.activity_evaluations.find_unresolved_by_skill_experience_id(
                experience.id
            )
        )
        if (
            experience.status
            not in {SkillExperienceStatus.LEARNING, SkillExperienceStatus.COMPLETED}
            or progress is None
            or not progress.content_released
            or unresolved is not None
        ):
            raise ConflictError

        active = repositories.ordering_passages.find_active(experience.id, activity_id)
        keyed = repositories.ordering_passages.find_by_key(
            experience.id, activity_id, passage_key
        )
        if keyed is not None and keyed.status == 'consumed':
            raise ConflictError
        if active is not None and active.passage_key != passage_key:
            raise ConflictError

        if active is not None:
            snapshot = active.grading_snapshot
            if active.activity_revision != activity_revision:
                raise ConflictError
        else:
            snapshot = self._curriculum_content_provider.get_learning_activity(
                activity_id
            )
            if snapshot is None or snapshot.revision != activity_revision:
                raise ConflictError

        if (
            snapshot.id != activity_id
            or snapshot.competency_id != competency_id
            or snapshot.activity_type != 'learning'
        ):
            raise ConflictError
        return experience.id, active, snapshot

    @staticmethod
    def _previous_ordering(
        active: OrderingPassage | None,
        answer: OrderingAnswerSubmission,
    ) -> VerifiedOrdering | None:
        if active is None:
            return None
        previous = next(
            (
                item
                for item in active.verified_orderings
                if item.question_key == answer.question_key
            ),
            None,
        )
        if (
            previous is not None
            and previous.ordered_step_keys != answer.ordered_step_keys
        ):
            raise ConflictError
        return previous

    @staticmethod
    def _ordering_result(result: VerifiedOrdering) -> PreliminaryQuestionResult:
        return PreliminaryQuestionResult(
            status='conclusive',
            score=result.score,
            is_correct=result.is_correct,
            explanation=result.explanation,
        )

    @staticmethod
    def pair_matching_result(
        question: CurriculumPairMatchingQuestionSnapshot,
        answer: PreviewAnswer,
    ) -> PreliminaryQuestionResult:
        if not isinstance(answer, PairMatchingAnswer):
            raise ValidationError

        result = PairMatchingScoring.evaluate(question, answer)
        return PreliminaryQuestionResult(
            status='conclusive',
            score=result.score,
            explanation=result.explanation,
            is_correct=result.outcome == 'full',
            submitted_pairs=answer.pairs,
            correct_pair_count=result.correct_pair_count,
            total_pair_count=result.total_pair_count,
            outcome=result.outcome,
        )

    @staticmethod
    def fill_blanks_result(
        question: CurriculumFillBlanksQuestionSnapshot,
        answer: PreviewAnswer,
    ) -> PreliminaryQuestionResult:
        if not isinstance(answer, FillBlanksAnswer):
            raise ValidationError

        result = FillBlanksScoring.score(question, answer)
        return PreliminaryQuestionResult(
            status='conclusive',
            score=result.score,
            is_correct=result.is_correct,
            explanation=result.explanation,
            correct_blank_count=len(result.correct_blank_keys),
            blank_count=result.blank_count,
        )

    @staticmethod
    def build_code_assessment_input(
        question: CodeQuestionSnapshot,
        part: CurriculumCodeRubricPartSnapshot,
        answer: CodeAnswer,
        max_bytes: int = CodeAnswerValidation.MAX_ASSESSMENT_INPUT_BYTES,
    ) -> CodeRubricAssessmentInput:
        return CodeAnswerValidation.build_assessment_input(
            question, part, answer, max_bytes
        )

    @staticmethod
    def _score_rubric(
        part: CurriculumCodeRubricPartSnapshot
        | CurriculumTranslationRubricPartSnapshot,
        concept_criteria: tuple[CurriculumCodeConceptCriterionSnapshot, ...],
        decisions: CodeRubricDecisions,
    ) -> tuple[
        tuple[CodeCriterionResult, ...],
        tuple[CodeConceptObservationResult, ...],
        Decimal | None,
    ]:
        criterion_by_key = {item.key: item.level for item in decisions.criterion_levels}
        concept_by_id = {
            item.concept_id: item.level for item in decisions.concept_levels
        }
        if set(criterion_by_key) != {item.key for item in part.criteria} or set(
            concept_by_id
        ) != {item.concept_id for item in concept_criteria}:
            raise ServiceUnavailableError

        criteria: list[CodeCriterionResult] = []
        mandatory_inconclusive = False
        for item in part.criteria:
            level = criterion_by_key[item.key]
            if level == 'inconclusive':
                comment = item.inconclusive_comment
                mandatory_inconclusive |= item.required
            else:
                comment = next(
                    (value for value in item.fixed_comments if value.level == level),
                    None,
                )
                if comment is None:
                    raise ServiceUnavailableError
            criteria.append(
                CodeCriterionResult(
                    key=item.key,
                    weight_percentage=item.weight_percentage,
                    level=level,
                    comment_id=comment.id,
                    comment=comment.text,
                )
            )
        concepts: list[CodeConceptObservationResult] = []
        for item in concept_criteria:
            level = concept_by_id[item.concept_id]
            observation = (
                item.inconclusive_observation
                if level == 'inconclusive'
                else next(
                    (
                        value
                        for value in item.level_observations
                        if value.level == level
                    ),
                    None,
                )
            )
            if observation is None:
                raise ServiceUnavailableError

            concepts.append(
                CodeConceptObservationResult(
                    concept_id=item.concept_id,
                    level=level,
                    observation_id=observation.id,
                )
            )
        score = (
            None
            if mandatory_inconclusive
            else sum(
                (
                    Decimal(value.level if isinstance(value.level, int) else 0)
                    * value.weight_percentage
                    / Decimal(100)
                    for value in criteria
                ),
                Decimal(0),
            )
        )
        if any(item.level == 'inconclusive' for item in criteria):
            score = None
        return tuple(criteria), tuple(concepts), score

    @staticmethod
    def code_result(
        question: CodeQuestionSnapshot,
        part: CurriculumCodeRubricPartSnapshot,
        answer: CodeAnswer,
        decisions: CodeRubricDecisions,
        max_bytes: int = CodeAnswerValidation.MAX_ASSESSMENT_INPUT_BYTES,
    ) -> PreliminaryQuestionResult:
        criteria, concepts, score = (
            PreviewActivityQuestionFeedbackUseCase._score_rubric(
                part, question.concept_criteria, decisions
            )
        )
        project = PreviewActivityQuestionFeedbackUseCase.build_code_assessment_input(
            question, part, answer, max_bytes
        )
        return PreliminaryQuestionResult(
            status='inconclusive' if score is None else 'conclusive',
            score=score,
            criteria=criteria,
            concept_observations=concepts,
            submitted_files=tuple(
                CodeSubmittedFile(path=path, content=content)
                for path, content in project.project_files
            ),
        )

    @staticmethod
    def translation_result(
        question: CurriculumTranslationQuestionSnapshot,
        part: CurriculumTranslationRubricPartSnapshot,
        answer: TranslationAnswer,
        decisions: CodeRubricDecisions,
    ) -> PreliminaryQuestionResult:
        criteria, concepts, score = (
            PreviewActivityQuestionFeedbackUseCase._score_rubric(
                part, question.concept_criteria, decisions
            )
        )
        return PreliminaryQuestionResult(
            status='inconclusive' if score is None else 'conclusive',
            score=score,
            criteria=criteria,
            concept_observations=concepts,
            submitted_text=answer.text,
        )
