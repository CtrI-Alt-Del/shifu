from decimal import Decimal

from shifu.learning.core.domain.structures import (
    ChoiceAnswerSubmission,
    CodeAnswer,
    CodeSubmittedFile,
    CodeCriterionResult,
    CodeConceptObservationResult,
)
from shifu.learning.core.use_cases.get_choice_activity_use_case import (
    GetChoiceActivityUseCase,
)
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
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumReactQuestionSnapshot,
    CurriculumReactFastifyQuestionSnapshot,
    CurriculumCodeRubricPartSnapshot,
)
from shifu.shared.core.interfaces import (
    CodeRubricAssessorProvider,
    CurriculumContentProvider,
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


class PreviewActivityQuestionFeedbackUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        code_rubric_assessor_provider: CodeRubricAssessorProvider,
        max_code_assessment_input_bytes: int = 262144,
    ) -> None:
        self._learning_database = learning_database
        self._curriculum_content_provider = curriculum_content_provider
        self._code_rubric_assessor_provider = code_rubric_assessor_provider
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
        answer: ChoiceAnswerSubmission | CodeAnswer,
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
                CurriculumJavascriptStdinQuestionSnapshot,
                CurriculumReactQuestionSnapshot,
                CurriculumReactFastifyQuestionSnapshot,
            ),
        ):
            if not isinstance(answer, CodeAnswer):
                raise ValidationError

            part = next(
                (item for item in snapshot.parts if item.question_key == question_key),
                None,
            )
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
    def code_result(
        question: CodeQuestionSnapshot,
        part: CurriculumCodeRubricPartSnapshot,
        answer: CodeAnswer,
        decisions: CodeRubricDecisions,
        max_bytes: int = CodeAnswerValidation.MAX_ASSESSMENT_INPUT_BYTES,
    ) -> PreliminaryQuestionResult:
        criterion_by_key = {item.key: item.level for item in decisions.criterion_levels}
        concept_by_id = {
            item.concept_id: item.level for item in decisions.concept_levels
        }
        if set(criterion_by_key) != {item.key for item in part.criteria} or set(
            concept_by_id
        ) != {item.concept_id for item in question.concept_criteria}:
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
        for item in question.concept_criteria:
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
        project = PreviewActivityQuestionFeedbackUseCase.build_code_assessment_input(
            question, part, answer, max_bytes
        )
        return PreliminaryQuestionResult(
            status='inconclusive' if score is None else 'conclusive',
            score=score,
            criteria=tuple(criteria),
            concept_observations=tuple(concepts),
            submitted_files=tuple(
                CodeSubmittedFile(path=path, content=content)
                for path, content in project.project_files
            ),
        )
