from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from shifu.learning.core.domain.structures import (
    ChoiceAnswerSubmission,
    OrderingAnswerSubmission,
    CodeAnswer,
    CodeSubmittedFile,
    FillBlanksAnswer,
    FillBlanksPlacement,
    PairMatchingAnswer,
    PairMatchingSelection,
    TranslationAnswer,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.preview_activity_question_feedback_use_case import (
    PreliminaryQuestionResult,
    PreviewActivityQuestionFeedbackUseCase,
    PreviewAnswer,
)
from shifu.learning.pipes import LearningPipe
from shifu.learning.rest.controllers.answer_request_shape import (
    validate_answer_request_shape,
)
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    AccountActivityProvider,
    CodeRubricAssessorProvider,
    CurriculumContentProvider,
    IdentifierProvider,
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


class PairRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    word_key: str = Field(min_length=1, max_length=128)
    translation_key: str = Field(min_length=1, max_length=128)


class AnswerRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    kind: Literal[
        'single_choice',
        'multiple_selection',
        'javascript_stdin',
        'react',
        'html_css_js',
        'react_fastify',
        'ordering',
        'fill_blanks',
        'translation',
        'pair_matching',
        'image_choice',
    ]
    question_key: str = Field(min_length=1, max_length=128)
    selected_option_keys: tuple[str, ...] | None = None
    files: tuple[SubmittedFileRequest, ...] | None = None
    ordered_step_keys: tuple[str, ...] | None = None
    placements: tuple[PlacementRequest, ...] | None = None
    text: str | None = None
    pairs: tuple[PairRequest, ...] | None = Field(default=None, max_length=8)

    @model_validator(mode='after')
    def validate_answer_shape(self) -> 'AnswerRequest':
        validate_answer_request_shape(
            self.kind,
            self.text,
            self.files,
            self.selected_option_keys,
            self.ordered_step_keys,
            self.placements,
            self.pairs,
        )
        return self


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    activity_revision: str = Field(min_length=1, max_length=128)
    passage_key: str | None = Field(default=None, min_length=1, max_length=36)
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


class PairResponse(BaseModel):
    word_key: str
    translation_key: str


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
    submitted_pairs: tuple[PairResponse, ...] | None = None
    correct_pair_count: int | None = None
    total_pair_count: int | None = None
    outcome: Literal['full', 'partial', 'incorrect'] | None = None
    option_feedback: str | None = None


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
            identifiers: Annotated[
                IdentifierProvider, Depends(LearningPipe.get_identifier_provider)
            ],
            translation_assessor: Annotated[
                TranslationRubricAssessorProvider,
                Depends(LearningPipe.get_translation_rubric_assessor_provider),
            ],
            account_activity_provider: Annotated[
                AccountActivityProvider,
                Depends(LearningPipe.get_account_activity_provider),
            ],
            max_assessment_bytes: Annotated[
                int, Depends(LearningPipe.get_max_code_assessment_input_bytes)
            ],
        ) -> Response:
            payload = request.answer
            if payload.kind == 'ordering':
                answer: PreviewAnswer = OrderingAnswerSubmission(
                    question_key=payload.question_key,
                    ordered_step_keys=payload.ordered_step_keys or (),
                )
            elif payload.kind == 'fill_blanks':
                answer = FillBlanksAnswer(
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
            elif payload.kind == 'pair_matching':
                answer = PairMatchingAnswer(
                    question_key=payload.question_key,
                    pairs=tuple(
                        PairMatchingSelection(
                            word_key=item.word_key,
                            translation_key=item.translation_key,
                        )
                        for item in (payload.pairs or ())
                    ),
                )
            else:
                answer = ChoiceAnswerSubmission(
                    question_key=payload.question_key,
                    selected_option_keys=payload.selected_option_keys or (),
                )
            result: PreliminaryQuestionResult = PreviewActivityQuestionFeedbackUseCase(
                database,
                provider,
                assessor,
                max_code_assessment_input_bytes=max_assessment_bytes,
                identifier_provider=identifiers,
                translation_rubric_assessor_provider=translation_assessor,
                account_activity_provider=account_activity_provider,
            ).execute(
                user.account_id,
                goal_id,
                skill_id,
                competency_id,
                activity_id,
                question_key,
                request.activity_revision,
                answer,
                request.passage_key,
            )
            return _RESPONSE_ADAPTER.validate_python(result, from_attributes=True)
