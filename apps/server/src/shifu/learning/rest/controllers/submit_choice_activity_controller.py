from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Header,
    Path,
    Request as FastAPIRequest,
    Response as FastAPIResponse,
    status,
)
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from shifu.learning.core.domain.structures import (
    ChoiceAnswerSubmission,
    ChoiceSubmissionOutcome,
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
from shifu.learning.core.use_cases import SubmitChoiceActivityUseCase
from shifu.learning.pipes import LearningPipe
from shifu.learning.rest.controllers.answer_request_shape import (
    validate_answer_request_shape,
)
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)
from shifu.shared.pipes import AuthenticationPipe
from shifu.shared.core.interfaces.telemetry_provider import (
    TelemetryEventInput,
    TelemetryProvider,
)
from shifu.shared.rest.pipes.telemetry_pipe import TelemetryPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class SubmittedFileRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    path: str
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

    question_key: str
    kind: (
        Literal[
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
        ]
        | None
    ) = None
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

    submission_key: UUID
    passage_key: UUID | None = None
    answers: tuple[AnswerRequest, ...]
    activity_revision: str | None = None


class Response(BaseModel):
    attempt_id: str
    status: Literal['pending']
    result_url: str
    is_diagnostic: bool = False


_OUTCOME_ADAPTER = TypeAdapter[ChoiceSubmissionOutcome](ChoiceSubmissionOutcome)


class SubmitChoiceActivityController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}'
            '/activities/{activity_id}/attempts',
            response_model=Response,
            status_code=status.HTTP_201_CREATED,
        )
        def _(
            http_request: FastAPIRequest,
            request: Request,
            response: FastAPIResponse,
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            skill_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            competency_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            activity_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            user: Annotated[
                AuthenticatedUser,
                Depends(AuthenticationPipe.get_authenticated_user),
            ],
            database: Annotated[
                LearningDatabase,
                Depends(LearningPipe.get_database),
            ],
            provider: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
            clock: Annotated[ClockProvider, Depends(LearningPipe.get_clock_provider)],
            identifiers: Annotated[
                IdentifierProvider,
                Depends(LearningPipe.get_identifier_provider),
            ],
            telemetry_provider: Annotated[
                TelemetryProvider | None,
                Depends(TelemetryPipe.get_telemetry_provider),
            ],
            max_assessment_bytes: Annotated[
                int, Depends(LearningPipe.get_max_code_assessment_input_bytes)
            ],
            diagnostic_run_id: Annotated[
                UUID | None,
                Header(alias='X-Diagnostic-Run-Id'),
            ] = None,
        ) -> Response:
            outcome = _OUTCOME_ADAPTER.validate_python(
                SubmitChoiceActivityUseCase(
                    database,
                    provider,
                    clock,
                    identifiers,
                    max_assessment_bytes,
                ).execute(
                    user.account_id,
                    goal_id,
                    skill_id,
                    competency_id,
                    activity_id,
                    str(request.submission_key),
                    tuple(
                        OrderingAnswerSubmission(
                            question_key=answer.question_key,
                            ordered_step_keys=answer.ordered_step_keys or (),
                        )
                        if answer.kind == 'ordering'
                        else FillBlanksAnswer(
                            question_key=answer.question_key,
                            placements=tuple(
                                FillBlanksPlacement(
                                    blank_key=item.blank_key, word_key=item.word_key
                                )
                                for item in (answer.placements or ())
                            ),
                        )
                        if answer.kind == 'fill_blanks'
                        else CodeAnswer(
                            question_key=answer.question_key,
                            kind=answer.kind,
                            files=tuple(
                                CodeSubmittedFile(path=item.path, content=item.content)
                                for item in (answer.files or ())
                            ),
                        )
                        if answer.kind
                        in {'javascript_stdin', 'react', 'html_css_js', 'react_fastify'}
                        else TranslationAnswer(
                            question_key=answer.question_key,
                            text=answer.text or '',
                        )
                        if answer.kind == 'translation'
                        else PairMatchingAnswer(
                            question_key=answer.question_key,
                            pairs=tuple(
                                PairMatchingSelection(
                                    word_key=item.word_key,
                                    translation_key=item.translation_key,
                                )
                                for item in (answer.pairs or ())
                            ),
                        )
                        if answer.kind == 'pair_matching'
                        else ChoiceAnswerSubmission(
                            question_key=answer.question_key,
                            selected_option_keys=answer.selected_option_keys or (),
                        )
                        for answer in request.answers
                    ),
                    request.activity_revision,
                    str(diagnostic_run_id) if diagnostic_run_id is not None else None,
                    user.time_zone,
                    str(request.passage_key)
                    if request.passage_key is not None
                    else None,
                ),
                from_attributes=True,
            )
            response.status_code = (
                status.HTTP_200_OK if outcome.replayed else status.HTTP_201_CREATED
            )
            if not outcome.replayed:
                event: TelemetryEventInput = {
                    'level': 'INFO',
                    'event': 'learning.attempt.submitted',
                    'operation': 'attempt.submit',
                    'result': 'success',
                }
                request_id = TelemetryPipe.get_request_id(http_request)
                if request_id is not None:
                    event['request_id'] = request_id
                TelemetryPipe.emit(telemetry_provider, event)
            return Response(
                attempt_id=outcome.attempt.attempt_id,
                status='pending',
                result_url=(
                    f'/learning/goals/{goal_id}/skills/{skill_id}/diagnostic'
                    if outcome.is_diagnostic
                    else f'/learning/goals/{goal_id}/skills/{skill_id}'
                    f'/competencies/{competency_id}/activities/{activity_id}'
                    f'/attempts/{outcome.attempt.attempt_id}'
                ),
                is_diagnostic=outcome.is_diagnostic,
            )
