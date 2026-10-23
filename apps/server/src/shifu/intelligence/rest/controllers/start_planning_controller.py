from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, PlainSerializer, TypeAdapter, field_validator

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import StartPlanningUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider
from shifu.shared.pipes import SharedPipe


class Request(BaseModel):
    initial_intent: str = Field(min_length=1)

    @field_validator('initial_intent')
    @classmethod
    def _strip_and_require_non_empty(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError('initial_intent must not be empty or whitespace-only')

        return stripped_value


class Response(BaseModel):
    id: str
    created_at: Annotated[
        datetime, PlainSerializer(lambda value: value.isoformat(), return_type=str)
    ]


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class StartPlanningController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/planning-sessions',
            response_model=Response,
            status_code=201,
        )
        def _(
            request: Request,
            user: Annotated[
                AuthenticatedUser,
                Depends(SharedPipe.get_authenticated_user),
            ],
            database: Annotated[
                IntelligenceDatabase,
                Depends(IntelligencePipe.get_database),
            ],
            identifier_provider: Annotated[
                IdentifierProvider,
                Depends(IntelligencePipe.get_identifier_provider),
            ],
            clock_provider: Annotated[
                ClockProvider,
                Depends(IntelligencePipe.get_clock_provider),
            ],
        ) -> Response:
            planning_session = StartPlanningUseCase(
                database,
                identifier_provider,
                clock_provider,
            ).execute(user.account_id, request.initial_intent)
            return _RESPONSE_ADAPTER.validate_python(
                planning_session, from_attributes=True
            )
