from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.domain.errors import EvaluationUnavailableError
from shifu.learning.core.domain.structures import (
    CodeAnswer,
    PreparedCodeActivityEvaluation,
    PreparedCodeQuestionAssessment,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.preview_activity_question_feedback_use_case import (
    PreviewActivityQuestionFeedbackUseCase,
)
from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import (
    CurriculumCodeRubricPartSnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumReactQuestionSnapshot,
    CurriculumReactFastifyQuestionSnapshot,
)


class PrepareCodeActivityEvaluationUseCase:
    def __init__(
        self, learning_database: LearningDatabase, max_input_bytes: int
    ) -> None:
        self._learning_database = learning_database
        self._max_input_bytes = max_input_bytes

    def execute(
        self, attempt_id: str, run_id: str
    ) -> PreparedCodeActivityEvaluation | None:
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

            prepared: list[PreparedCodeQuestionAssessment] = []
            for question in snapshot.questions:
                if not isinstance(
                    question,
                    (
                        CurriculumJavascriptStdinQuestionSnapshot,
                        CurriculumReactQuestionSnapshot,
                        CurriculumReactFastifyQuestionSnapshot,
                    ),
                ):
                    continue
                answer = answers[question.key]
                part = parts[question.key]
                if not isinstance(answer, CodeAnswer) or not isinstance(
                    part, CurriculumCodeRubricPartSnapshot
                ):
                    raise EvaluationUnavailableError
                try:
                    assessment_input = PreviewActivityQuestionFeedbackUseCase.build_code_assessment_input(
                        question, part, answer, self._max_input_bytes
                    )
                except ValidationError as error:
                    raise EvaluationUnavailableError from error
                size = sum(
                    len(path.encode()) + len(content.encode())
                    for path, content in assessment_input.project_files
                )
                if size > self._max_input_bytes:
                    raise EvaluationUnavailableError
                prepared.append(
                    PreparedCodeQuestionAssessment(
                        question_key=question.key,
                        assessment_input=assessment_input,
                    )
                )

        if not prepared:
            raise EvaluationUnavailableError
        return PreparedCodeActivityEvaluation(
            attempt_id=attempt_id,
            run_id=run_id,
            questions=tuple(prepared),
        )
