from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.gamification.core.domain.entities import XpGrant
from shifu.gamification.database.sqlalchemy.mappers import XpGrantMapper
from shifu.gamification.database.sqlalchemy.models import XpGrantModel


class SqlalchemyXpGrantsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, grant: XpGrant) -> None:
        self._session.add(XpGrantMapper.to_model(grant))

    def find_many_by_account_id(self, account_id: str) -> tuple[XpGrant, ...]:
        # The `id` tiebreak is required, not decorative: one achievement
        # cascade writes several rows sharing a single `granted_at`.
        models = (
            self._session.execute(
                select(XpGrantModel)
                .where(XpGrantModel.account_id == account_id)
                .order_by(XpGrantModel.granted_at.desc(), XpGrantModel.id.desc())
            )
            .scalars()
            .all()
        )
        return tuple(XpGrantMapper.to_domain(model) for model in models)

    def remove_many_by_account_id(self, account_id: str) -> None:
        self._session.execute(
            delete(XpGrantModel).where(XpGrantModel.account_id == account_id)
        )
