from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response as FastApiResponse,
)
from pydantic import BaseModel, TypeAdapter

from shifu.intelligence.core.domain.enums import LearnerMemoryCategory
from shifu.intelligence.core.domain.structures import LearnerMemoryFilter
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import ListLearnerMemoriesUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.learner_memory_schemas import LearnerMemorySchemas
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import MentorAccessProvider
from shifu.shared.pipes import SharedPipe


class Response(BaseModel):
    items: list[LearnerMemorySchemas.Memory]


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class ListLearnerMemoriesController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get('/learner-memories', response_model=Response, status_code=200)
        def _(
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
            q: str | None = None,
            category: LearnerMemoryCategory | None = None,
        ) -> Response:
            query = q.strip() if q is not None else None
            if (
                query is not None
                and len(query) > LearnerMemoryFilter.MAX_QUERY_CODE_POINTS
            ):
                raise HTTPException(
                    status_code=422,
                    detail={
                        'code': 'validation_error',
                        'message': 'A busca deve ter no máximo 100 caracteres.',
                    },
                )
            details = ListLearnerMemoriesUseCase(database, access).execute(
                user.account_id,
                LearnerMemoryFilter(query=query or None, category=category),
            )
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(
                {'items': details}, from_attributes=True
            )
