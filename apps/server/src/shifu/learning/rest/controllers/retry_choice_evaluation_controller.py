from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel, TypeAdapter

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import RetryChoiceEvaluationUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class Response(BaseModel):
    attempt_id: str
    activity_id: str
    status: str
    submitted_at: datetime
    retry_allowed: bool
    failure_message: str | None = None


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class RetryChoiceEvaluationController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}'
            '/activities/{activity_id}/attempts/{attempt_id}/retry',
            response_model=Response,
            response_model_exclude_none=True,
            status_code=status.HTTP_202_ACCEPTED,
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
            clock: Annotated[ClockProvider, Depends(LearningPipe.get_clock_provider)],
            identifiers: Annotated[
                IdentifierProvider,
                Depends(LearningPipe.get_identifier_provider),
            ],
        ) -> Response:
            detail = RetryChoiceEvaluationUseCase(
                database,
                clock,
                identifiers,
            ).execute(
                user.account_id,
                goal_id,
                skill_id,
                competency_id,
                activity_id,
                attempt_id,
            )
            return _RESPONSE_ADAPTER.validate_python(detail, from_attributes=True)
