from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.domain.errors import EvaluationUnavailableError
from shifu.learning.core.domain.structures import (
    PreparedTranslationActivityEvaluation,
    PreparedTranslationQuestionAssessment,
    TranslationAnswer,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.structures import (
    CurriculumLearningActivitySnapshot,
    CurriculumTranslationQuestionSnapshot,
    CurriculumTranslationRubricPartSnapshot,
    TranslationRubricAssessmentInput,
)


class PrepareTranslationActivityEvaluationUseCase:
    def __init__(self, learning_database: LearningDatabase) -> None:
        self._learning_database = learning_database

    def execute(
        self, attempt_id: str, run_id: str
    ) -> PreparedTranslationActivityEvaluation | None:
        with self._learning_database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
            if (
                attempt is None
                or evaluation is None
                or evaluation.run_id != run_id
                or evaluation.status is not ActivityEvaluationStatus.PENDING
                or not isinstance(
                    attempt.grading_snapshot, CurriculumLearningActivitySnapshot
                )
            ):
                return None

            snapshot = attempt.grading_snapshot
            answers = {answer.question_key: answer for answer in attempt.answers}
            questions = {question.key: question for question in snapshot.questions}
            parts = {part.question_key: part for part in snapshot.parts}
            if len(answers) != len(attempt.answers) or set(answers) != set(questions):
                raise EvaluationUnavailableError

            prepared: list[PreparedTranslationQuestionAssessment] = []
            for question in snapshot.questions:
                if not isinstance(question, CurriculumTranslationQuestionSnapshot):
                    continue
                answer = answers[question.key]
                part = parts[question.key]
                if not isinstance(answer, TranslationAnswer) or not isinstance(
                    part, CurriculumTranslationRubricPartSnapshot
                ):
                    raise EvaluationUnavailableError
                assessment_input = TranslationRubricAssessmentInput(
                    question_kind=question.kind,
                    source_text=question.source_text,
                    source_language=question.source_language,
                    target_language=question.target_language,
                    reference_translations=question.reference_translations,
                    submitted_text=answer.text,
                    rubric_criteria=part.criteria,
                    concept_criteria=question.concept_criteria,
                )
                prepared.append(
                    PreparedTranslationQuestionAssessment(
                        question_key=question.key,
                        assessment_input=assessment_input,
                    )
                )

        if not prepared:
            raise EvaluationUnavailableError
        return PreparedTranslationActivityEvaluation(
            attempt_id=attempt_id,
            run_id=run_id,
            questions=tuple(prepared),
        )
