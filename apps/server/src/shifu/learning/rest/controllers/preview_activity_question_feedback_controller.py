from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from shifu.learning.core.domain.structures import (
    ChoiceAnswerSubmission,
    CodeAnswer,
    CodeSubmittedFile,
    FillBlanksAnswer,
    FillBlanksPlacement,
    TranslationAnswer,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.preview_activity_question_feedback_use_case import (
    PreliminaryQuestionResult,
    PreviewActivityQuestionFeedbackUseCase,
)
from shifu.learning.pipes import LearningPipe
from shifu.learning.rest.controllers.answer_request_shape import (
    validate_answer_request_shape,
)
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    CodeRubricAssessorProvider,
    CurriculumContentProvider,
    TranslationRubricAssessorProvider,
)
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class SubmittedFileRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    path: str = Field(min_length=1, max_length=256)
    content: str


class PlacementRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    blank_key: str = Field(min_length=1, max_length=128)
    word_key: str = Field(min_length=1, max_length=128)


class AnswerRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    kind: Literal[
        'single_choice',
        'multiple_selection',
        'javascript_stdin',
        'react',
        'html_css_js',
        'react_fastify',
        'fill_blanks',
        'translation',
    ]
    question_key: str = Field(min_length=1, max_length=128)
    selected_option_keys: tuple[str, ...] | None = None
    files: tuple[SubmittedFileRequest, ...] | None = None
    placements: tuple[PlacementRequest, ...] | None = None
    text: str | None = None

    @model_validator(mode='after')
    def validate_answer_shape(self) -> 'AnswerRequest':
        validate_answer_request_shape(
            self.kind,
            self.text,
            self.files,
            self.selected_option_keys,
            self.placements,
        )
        return self


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    activity_revision: str = Field(min_length=1, max_length=128)
    answer: AnswerRequest


class CriterionResponse(BaseModel):
    key: str
    weight_percentage: int
    level: int | str
    comment_id: str
    comment: str


class ConceptResponse(BaseModel):
    concept_id: str
    level: int | str
    observation_id: str


class SubmittedFileResponse(BaseModel):
    path: str
    content: str


class Response(BaseModel):
    status: Literal['conclusive', 'inconclusive']
    score: Decimal | None
    explanation: str | None = None
    is_correct: bool | None = None
    criteria: tuple[CriterionResponse, ...] = ()
    concept_observations: tuple[ConceptResponse, ...] = ()
    submitted_files: tuple[SubmittedFileResponse, ...] = ()
    correct_blank_count: int | None = None
    blank_count: int | None = None
    submitted_text: str | None = None


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class PreviewActivityQuestionFeedbackController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}'
            '/activities/{activity_id}/questions/{question_key}/preliminary-evaluations',
            response_model=Response,
            response_model_exclude_none=True,
            status_code=200,
        )
        def _(
            request: Request,
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            skill_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            competency_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            activity_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            question_key: Annotated[str, Path(min_length=1, max_length=128)],
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[LearningDatabase, Depends(LearningPipe.get_database)],
            provider: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
            assessor: Annotated[
                CodeRubricAssessorProvider,
                Depends(LearningPipe.get_code_rubric_assessor_provider),
            ],
            translation_assessor: Annotated[
                TranslationRubricAssessorProvider,
                Depends(LearningPipe.get_translation_rubric_assessor_provider),
            ],
            max_assessment_bytes: Annotated[
                int, Depends(LearningPipe.get_max_code_assessment_input_bytes)
            ],
        ) -> Response:
            payload = request.answer
            if payload.kind == 'fill_blanks':
                answer: (
                    ChoiceAnswerSubmission
                    | CodeAnswer
                    | FillBlanksAnswer
                    | TranslationAnswer
                ) = FillBlanksAnswer(
                    question_key=payload.question_key,
                    placements=tuple(
                        FillBlanksPlacement(
                            blank_key=item.blank_key, word_key=item.word_key
                        )
                        for item in (payload.placements or ())
                    ),
                )
            elif payload.kind in {
                'javascript_stdin',
                'react',
                'html_css_js',
                'react_fastify',
            }:
                answer = CodeAnswer(
                    question_key=payload.question_key,
                    kind=payload.kind,
                    files=tuple(
                        CodeSubmittedFile(path=item.path, content=item.content)
                        for item in (payload.files or ())
                    ),
                )
            elif payload.kind == 'translation':
                answer = TranslationAnswer(
                    question_key=payload.question_key,
                    text=payload.text or '',
                )
            else:
                answer = ChoiceAnswerSubmission(
                    question_key=payload.question_key,
                    selected_option_keys=payload.selected_option_keys or (),
                )
            result: PreliminaryQuestionResult = PreviewActivityQuestionFeedbackUseCase(
                database, provider, assessor, translation_assessor, max_assessment_bytes
            ).execute(
                user.account_id,
                goal_id,
                skill_id,
                competency_id,
                activity_id,
                question_key,
                request.activity_revision,
                answer,
            )
            return _RESPONSE_ADAPTER.validate_python(result, from_attributes=True)
