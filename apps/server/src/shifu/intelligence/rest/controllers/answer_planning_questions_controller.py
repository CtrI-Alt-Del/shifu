from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import Response as FastApiResponse
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from shifu.intelligence.core.domain.structures import PlanningAnswer
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    PlanningSessionsRepository,
)
from shifu.intelligence.core.use_cases import AnswerPlanningQuestionsUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.planning_session_schemas import (
    PlanningSessionSchemas,
)
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider
from shifu.shared.pipes import SharedPipe


class _Answer(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question_id: str = Field(min_length=1, max_length=64)
    option_ids: list[str] = Field(max_length=8)
    other_text: str | None = Field(default=None, max_length=200)


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')
    batch_id: str = Field(min_length=1, max_length=64)
    answers: list[_Answer] = Field(max_length=8)


class Response(PlanningSessionSchemas.Detail):
    pass


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class AnswerPlanningQuestionsController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/planning-sessions/{planning_id}/answers',
            response_model=Response,
            status_code=202,
        )
        def _(
            planning_id: Annotated[
                str, Field(pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')
            ],
            request: Request,
            response: FastApiResponse,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            sessions: Annotated[
                PlanningSessionsRepository,
                Depends(IntelligencePipe.get_planning_sessions_repository),
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            identifier: Annotated[
                IdentifierProvider, Depends(IntelligencePipe.get_identifier_provider)
            ],
            clock: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
        ) -> Response:
            session = AnswerPlanningQuestionsUseCase(
                sessions, database, identifier, clock
            ).execute(
                user.account_id,
                planning_id,
                request.batch_id,
                tuple(
                    PlanningAnswer(
                        question_id=answer.question_id,
                        option_ids=tuple(answer.option_ids),
                        other_text=answer.other_text,
                    )
                    for answer in request.answers
                ),
            )
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(session, from_attributes=True)
