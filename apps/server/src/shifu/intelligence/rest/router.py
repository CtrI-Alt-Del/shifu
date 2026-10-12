from shifu.intelligence.rest.controllers.stream_mentor_response_controller import (
    StreamMentorResponseController,
)
from shifu.intelligence.rest.controllers.retry_mentor_response_controller import (
    RetryMentorResponseController,
)
from shifu.intelligence.rest.controllers.cancel_mentor_response_controller import (
    CancelMentorResponseController,
)
from shifu.intelligence.rest.controllers.submit_mentor_message_controller import (
    SubmitMentorMessageController,
)
from fastapi import APIRouter

from shifu.intelligence.rest.controllers.start_planning_controller import (
    StartPlanningController,
)
from shifu.intelligence.rest.controllers.create_mentor_session_controller import (
    CreateMentorSessionController,
)
from shifu.intelligence.rest.controllers.get_mentor_session_controller import (
    GetMentorSessionController,
)
from shifu.intelligence.rest.controllers.list_mentor_sessions_controller import (
    ListMentorSessionsController,
)
from shifu.intelligence.rest.controllers.remove_mentor_session_controller import (
    RemoveMentorSessionController,
)
from shifu.intelligence.rest.controllers.rename_mentor_session_controller import (
    RenameMentorSessionController,
)


class IntelligenceRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/intelligence', tags=['intelligence'])
        StartPlanningController.handle(router)
        CreateMentorSessionController.handle(router)
        ListMentorSessionsController.handle(router)
        GetMentorSessionController.handle(router)
        RenameMentorSessionController.handle(router)
        RemoveMentorSessionController.handle(router)
        SubmitMentorMessageController.handle(router)
        CancelMentorResponseController.handle(router)
        RetryMentorResponseController.handle(router)
        StreamMentorResponseController.handle(router)
        return router
