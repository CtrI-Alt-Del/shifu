from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.gamification.core.domain.entities import GamificationProfile
from shifu.gamification.database.sqlalchemy.mappers import GamificationProfileMapper
from shifu.gamification.database.sqlalchemy.models import GamificationProfileModel


class SqlalchemyGamificationProfilesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_account_id(self, account_id: str) -> GamificationProfile | None:
        model = self._session.scalar(
            select(GamificationProfileModel).where(
                GamificationProfileModel.account_id == account_id
            )
        )
        return GamificationProfileMapper.to_domain(model) if model is not None else None

    def add(self, profile: GamificationProfile) -> None:
        self._session.add(GamificationProfileMapper.to_model(profile))

    def update(self, profile: GamificationProfile) -> None:
        self._session.merge(GamificationProfileMapper.to_model(profile))

    def remove(self, profile: GamificationProfile) -> None:
        self._session.execute(
            delete(GamificationProfileModel).where(
                GamificationProfileModel.id == profile.id
            )
        )
