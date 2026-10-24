from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.gamification.core.use_cases import GetXpHistoryUseCase
from shifu.gamification.pipes import GamificationPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import AuthenticationPipe


class XpHistoryEntryResponse(BaseModel):
    id: str
    amount: int
    source: str
    title: str
    detail: str
    occurred_at: datetime = Field(serialization_alias='occurredAt')
    granted_at: datetime = Field(serialization_alias='grantedAt')


class Response(BaseModel):
    total_xp: int = Field(serialization_alias='totalXp')
    entries: tuple[XpHistoryEntryResponse, ...]


class GetXpHistoryController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/xp-history',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[
                GamificationDatabase, Depends(GamificationPipe.get_database)
            ],
        ) -> Response:
            history = GetXpHistoryUseCase(database).execute(user.account_id)
            return Response(
                total_xp=history.total_xp,
                entries=tuple(
                    XpHistoryEntryResponse(
                        id=entry.grant_id,
                        amount=entry.amount,
                        source=entry.source.value,
                        title=entry.title,
                        detail=entry.detail,
                        occurred_at=entry.occurred_at,
                        granted_at=entry.granted_at,
                    )
                    for entry in history.entries
                ),
            )
