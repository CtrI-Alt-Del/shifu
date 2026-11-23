from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, TypeAdapter

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import GetChoiceAttemptUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class NextActionResponse(BaseModel):
    competency_id: str
    activity_id: str
    difficulty: str
    type: str


class ChoiceQuestionResultResponse(BaseModel):
    question_key: str
    prompt: str
    selected_option_keys: tuple[str, ...]
    score: Decimal
    is_correct: bool
    explanation: str
    disclosed_correct_option_keys: tuple[str, ...]


class SubmittedFileResponse(BaseModel):
    path: str
    content: str


class CriterionResultResponse(BaseModel):
    key: str
    weight_percentage: int
    level: int | str
    comment_id: str
    comment: str


class ConceptObservationResponse(BaseModel):
    concept_id: str
    level: int | str
    observation_id: str


class CodeQuestionResultResponse(BaseModel):
    question_key: str
    kind: str
    prompt: str
    submitted_files: tuple[SubmittedFileResponse, ...]
    score: Decimal | None
    criterion_results: tuple[CriterionResultResponse, ...]
    concept_observations: tuple[ConceptObservationResponse, ...]


class OrderingStepResultResponse(BaseModel):
    key: str
    text: str


class OrderingQuestionResultResponse(BaseModel):
    question_key: str
    kind: Literal['ordering']
    prompt: str
    steps: tuple[OrderingStepResultResponse, ...]
    submitted_step_keys: tuple[str, ...]
    score: Decimal
    is_correct: bool
    explanation: str
    accepted_orders: tuple[tuple[str, ...], ...] = ()


class ImageChoiceOptionResultResponse(BaseModel):
    key: str
    image_path: str
    description: str


class ImageChoiceQuestionResultResponse(BaseModel):
    question_key: str
    kind: Literal['image_choice']
    prompt: str
    options: tuple[ImageChoiceOptionResultResponse, ...]
    selected_option_key: str
    score: Decimal
    is_correct: bool
    option_feedback: str
    explanation: str
    disclosed_correct_option_key: str | None = None


class FillBlanksSegmentResponse(BaseModel):
    text: str | None
    blank_key: str | None


class FillBlanksWordResponse(BaseModel):
    key: str
    word: str


class FillBlanksPlacementResponse(BaseModel):
    blank_key: str
    word_key: str


class FillBlanksExpectedBlankResponse(BaseModel):
    blank_key: str
    accepted_words: tuple[str, ...]


class FillBlanksQuestionResultResponse(BaseModel):
    question_key: str
    kind: Literal['fill_blanks']
    prompt: str
    content_language: str
    segments: tuple[FillBlanksSegmentResponse, ...]
    bank: tuple[FillBlanksWordResponse, ...]
    placements: tuple[FillBlanksPlacementResponse, ...]
    score: Decimal
    is_correct: bool
    correct_blank_count: int
    blank_count: int
    explanation: str
    disclosed_expected_blanks: tuple[FillBlanksExpectedBlankResponse, ...]


class TranslationQuestionResultResponse(BaseModel):
    question_key: str
    kind: str
    prompt: str
    submitted_text: str
    score: Decimal | None
    criterion_results: tuple[CriterionResultResponse, ...]
    concept_observations: tuple[ConceptObservationResponse, ...]


class PairResultResponse(BaseModel):
    word_key: str
    translation_key: str


class PairMatchingQuestionResultResponse(BaseModel):
    question_key: str
    kind: Literal['pair_matching']
    prompt: str
    submitted_pairs: tuple[PairResultResponse, ...]
    score: Decimal
    correct_pair_count: int
    total_pair_count: int
    outcome: Literal['full', 'partial', 'incorrect']
    explanation: str
    disclosed_correct_pairs: tuple[PairResultResponse, ...] = ()


class PracticalRecordResultResponse(BaseModel):
    key: str
    label: str


class PracticalPhotoResultResponse(BaseModel):
    record_key: str
    photo_id: str


class PracticalCriterionResultResponse(BaseModel):
    key: str
    name: str
    weight: Decimal
    level: int | None
    comment: str | None


class PracticalUnassessableRecordResponse(BaseModel):
    key: str
    label: str
    comment: str


class PracticalPreparationQuestionResultResponse(BaseModel):
    question_key: str
    kind: Literal['practical_preparation']
    prompt: str
    records: tuple[PracticalRecordResultResponse, ...]
    photos: tuple[PracticalPhotoResultResponse, ...]
    reflection: str
    criteria: tuple[PracticalCriterionResultResponse, ...]
    score: Decimal | None
    closed_without_grade: bool
    unassessable_records: tuple[PracticalUnassessableRecordResponse, ...]
    guidance: str | None


class Response(BaseModel):
    attempt_id: str
    activity_id: str
    status: str
    submitted_at: datetime
    retry_allowed: bool
    failure_message: str | None = None
    score: Decimal | None = None
    progress_before: Decimal | None = None
    progress_after: Decimal | None = None
    status_before: str | None = None
    status_after: str | None = None
    next_action: NextActionResponse | None = None
    completes_skill: bool = False
    questions: tuple[
        ChoiceQuestionResultResponse
        | CodeQuestionResultResponse
        | OrderingQuestionResultResponse
        | FillBlanksQuestionResultResponse
        | TranslationQuestionResultResponse
        | PairMatchingQuestionResultResponse
        | ImageChoiceQuestionResultResponse
        | PracticalPreparationQuestionResultResponse,
        ...,
    ] = ()


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetChoiceAttemptController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}'
            '/activities/{activity_id}/attempts/{attempt_id}',
            response_model=Response,
            response_model_exclude_none=True,
            response_model_exclude_defaults=True,
            status_code=200,
        )
        def _(
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            skill_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            competency_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            activity_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            attempt_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
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
        ) -> Response:
            detail = GetChoiceAttemptUseCase(
                database,
                provider,
                clock,
            ).execute(
                user.account_id,
                goal_id,
                skill_id,
                competency_id,
                activity_id,
                attempt_id,
            )
            return _RESPONSE_ADAPTER.validate_python(detail, from_attributes=True)
