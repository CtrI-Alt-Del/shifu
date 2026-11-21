from decimal import Decimal

from shifu.learning.core.domain.structures import (
    ChoiceAnswerSubmission,
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
from shifu.learning.core.interfaces import LearningDatabase
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
    CurriculumFillBlanksQuestionSnapshot,
    CurriculumPairMatchingQuestionSnapshot,
    CurriculumTranslationQuestionSnapshot,
    CurriculumTranslationRubricPartSnapshot,
    TranslationRubricAssessmentInput,
)
from shifu.shared.core.interfaces import (
    CodeRubricAssessorProvider,
    CurriculumContentProvider,
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


type PreviewAnswer = (
    ChoiceAnswerSubmission
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
    ) -> None:
        self._learning_database = learning_database
        self._curriculum_content_provider = curriculum_content_provider
        self._code_rubric_assessor_provider = code_rubric_assessor_provider
        self._translation_rubric_assessor_provider = (
            translation_rubric_assessor_provider
        )
        self._max_code_assessment_input_bytes = max_code_assessment_input_bytes

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
    ) -> PreliminaryQuestionResult:
        detail = GetChoiceActivityUseCase(
            self._learning_database, self._curriculum_content_provider
        ).execute(account_id, goal_id, skill_id, competency_id, activity_id)
        if detail.activity_revision != activity_revision:
            raise ConflictError

        snapshot = self._curriculum_content_provider.get_learning_activity(activity_id)
        if snapshot is None or snapshot.revision != activity_revision:
            raise ConflictError

        question = next(
            (item for item in snapshot.questions if item.key == question_key), None
        )
        if question is None or answer.question_key != question_key:
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

        if not isinstance(answer, ChoiceAnswerSubmission):
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
