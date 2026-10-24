from pathlib import PurePosixPath

from shifu.learning.core.domain.structures import CodeAnswer, CodeSubmittedFile
from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import (
    CodeRubricAssessmentInput,
    CurriculumCodeRubricPartSnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumReactQuestionSnapshot,
    CurriculumHtmlCssJsQuestionSnapshot,
)

type CodeQuestionSnapshot = (
    CurriculumJavascriptStdinQuestionSnapshot
    | CurriculumReactQuestionSnapshot
    | CurriculumHtmlCssJsQuestionSnapshot
)


class CodeAnswerValidation:
    MAX_ASSESSMENT_INPUT_BYTES = 262144

    @staticmethod
    def normalize(
        question: CodeQuestionSnapshot,
        answer: CodeAnswer,
        max_bytes: int = MAX_ASSESSMENT_INPUT_BYTES,
    ) -> CodeAnswer:
        editable_paths = {item.path for item in question.initial_files if item.editable}
        initial_paths = {item.path for item in question.initial_files}
        provided = {item.path: item.content for item in answer.files}
        if (
            answer.source_code is not None
            or (answer.kind is not None and answer.kind != question.kind)
            or (question.kind == 'html_css_js' and answer.kind != question.kind)
            or len(provided) != len(answer.files)
            or not editable_paths.issubset(provided)
        ):
            raise ValidationError

        additional_paths = set(provided) - editable_paths
        if additional_paths & initial_paths:
            raise ValidationError
        if not isinstance(question, CurriculumReactQuestionSnapshot):
            if additional_paths:
                raise ValidationError
        else:
            policy = question.additional_file_policy
            if (
                len(additional_paths) > (policy.max_files if policy else 0)
                or (additional_paths and policy is None)
                or any(
                    policy is None or not policy.allows(path)
                    for path in additional_paths
                )
            ):
                raise ValidationError

        project = {item.path: item.content for item in question.initial_files}
        project.update(provided)
        paths = tuple(project)
        path_set = set(paths)
        if any(
            '/'.join(PurePosixPath(path).parts[:index]) in path_set
            for path in paths
            for index in range(1, len(PurePosixPath(path).parts))
        ):
            raise ValidationError

        if CodeAnswerValidation._project_size(project) > max_bytes:
            raise ValidationError

        return CodeAnswer(
            question_key=answer.question_key,
            files=tuple(
                CodeSubmittedFile(path=path, content=content)
                for path, content in sorted(provided.items())
            ),
            kind=question.kind if question.kind != 'javascript_stdin' else None,
        )

    @staticmethod
    def build_assessment_input(
        question: CodeQuestionSnapshot,
        part: CurriculumCodeRubricPartSnapshot,
        answer: CodeAnswer,
        max_bytes: int = MAX_ASSESSMENT_INPUT_BYTES,
    ) -> CodeRubricAssessmentInput:
        normalized = CodeAnswerValidation.normalize(question, answer, max_bytes)
        submitted = {item.path: item.content for item in normalized.files}
        project = {item.path: item.content for item in question.initial_files}
        project.update(submitted)
        return CodeRubricAssessmentInput(
            question_kind=question.kind,
            prompt=question.prompt,
            project_files=tuple(sorted(project.items())),
            submitted_paths=tuple(sorted(submitted)),
            rubric_criteria=part.criteria,
            concept_criteria=question.concept_criteria,
        )

    @staticmethod
    def _project_size(project: dict[str, str]) -> int:
        return sum(
            len(path.encode('utf-8')) + len(content.encode('utf-8'))
            for path, content in project.items()
        )
