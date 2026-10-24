from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Response as FastApiResponse,
)
from pydantic import TypeAdapter

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import GetLearnerMemoryUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.learner_memory_schemas import LearnerMemorySchemas
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import MentorAccessProvider
from shifu.shared.pipes import SharedPipe


class Response(LearnerMemorySchemas.Memory):
    pass


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetLearnerMemoryController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/learner-memories/{memory_id}', response_model=Response, status_code=200
        )
        def _(
            memory_id: str,
            response: FastApiResponse,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            access: Annotated[
                MentorAccessProvider,
                Depends(IntelligencePipe.get_mentor_access_provider),
            ],
        ) -> Response:
            details = GetLearnerMemoryUseCase(database, access).execute(
                user.account_id, memory_id
            )
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(details, from_attributes=True)
