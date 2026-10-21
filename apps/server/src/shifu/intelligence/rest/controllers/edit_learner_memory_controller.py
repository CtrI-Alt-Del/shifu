from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response as FastApiResponse,
)
from pydantic import BaseModel, ConfigDict, Field, StrictInt, TypeAdapter

from shifu.intelligence.core.domain.errors import LearnerMemoryContentInvalidError
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    LearnerMemoryAnalyzerProvider,
)
from shifu.intelligence.core.use_cases import EditLearnerMemoryUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.learner_memory_schemas import LearnerMemorySchemas
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider
from shifu.shared.pipes import SharedPipe


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    content: str
    expected_version: Annotated[StrictInt, Field(ge=1)]


class Response(LearnerMemorySchemas.Memory):
    pass


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class EditLearnerMemoryController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.patch(
            '/learner-memories/{memory_id}', response_model=Response, status_code=200
        )
        def _(
            memory_id: str,
            request: Request,
            response: FastApiResponse,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            analyzer: Annotated[
                LearnerMemoryAnalyzerProvider,
                Depends(IntelligencePipe.get_learner_memory_analyzer_provider),
            ],
            access: Annotated[
                MentorAccessProvider,
                Depends(IntelligencePipe.get_mentor_access_provider),
            ],
            clock_provider: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
        ) -> Response:
            try:
                details = EditLearnerMemoryUseCase(
                    database, analyzer, access, clock_provider
                ).execute(
                    user.account_id,
                    memory_id,
                    request.content,
                    request.expected_version,
                )
            except LearnerMemoryContentInvalidError as error:
                # The shared handler maps domain validation to 400; this contract is 422.
                raise HTTPException(
                    status_code=422,
                    detail={'code': 'validation_error', 'message': error.message},
                ) from error
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(details, from_attributes=True)
