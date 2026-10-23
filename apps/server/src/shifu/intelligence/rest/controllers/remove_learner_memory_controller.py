from typing import Annotated

from fastapi import APIRouter, Depends, Response

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import RemoveLearnerMemoryUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider
from shifu.shared.pipes import SharedPipe


class RemoveLearnerMemoryController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.delete(
            '/learner-memories/{memory_id}',
            response_model=None,
            status_code=204,
        )
        def _(
            memory_id: str,
            response: Response,
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
            clock_provider: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
        ) -> Response:
            RemoveLearnerMemoryUseCase(database, access, clock_provider).execute(
                user.account_id, memory_id
            )
            response.headers['Cache-Control'] = 'private, no-store'
            response.status_code = 204
            return response
