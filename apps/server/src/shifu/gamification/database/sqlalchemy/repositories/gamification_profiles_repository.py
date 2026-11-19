from datetime import date

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

    def find_by_account_id_for_update(
        self, account_id: str
    ) -> GamificationProfile | None:
        # Writers load the profile here and write the whole row back, so the
        # row stays locked until the transaction ends. A concurrent
        # read-modify-write then waits and reads the committed values instead
        # of overwriting them with stale ones.
        model = self._session.scalar(
            select(GamificationProfileModel)
            .where(GamificationProfileModel.account_id == account_id)
            .with_for_update()
        )
        return GamificationProfileMapper.to_domain(model) if model is not None else None

    def find_many_reminder_candidates(
        self,
        *,
        practiced_since: date,
        after_account_id: str | None,
        limit: int,
    ) -> tuple[GamificationProfile, ...]:
        statement = select(GamificationProfileModel).where(
            GamificationProfileModel.streak_latest_practice_date >= practiced_since
        )
        if after_account_id is not None:
            statement = statement.where(
                GamificationProfileModel.account_id > after_account_id
            )
        models = self._session.scalars(
            statement.order_by(GamificationProfileModel.account_id).limit(limit)
        )
        return tuple(GamificationProfileMapper.to_domain(model) for model in models)

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
