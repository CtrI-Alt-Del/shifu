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
        return router
