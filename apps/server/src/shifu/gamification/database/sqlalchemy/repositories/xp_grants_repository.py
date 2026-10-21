from sqlalchemy import delete
from sqlalchemy.orm import Session

from shifu.gamification.core.domain.entities import XpGrant
from shifu.gamification.database.sqlalchemy.mappers import XpGrantMapper
from shifu.gamification.database.sqlalchemy.models import XpGrantModel


class SqlalchemyXpGrantsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, grant: XpGrant) -> None:
        self._session.add(XpGrantMapper.to_model(grant))

    def remove_many_by_account_id(self, account_id: str) -> None:
        self._session.execute(
            delete(XpGrantModel).where(XpGrantModel.account_id == account_id)
        )
