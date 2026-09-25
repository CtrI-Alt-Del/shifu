from datetime import datetime

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from shifu.identity.core.domain.entities import Account
from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.database.sqlalchemy.mappers import AccountMapper
from shifu.identity.database.sqlalchemy.models import AccountModel


class SqlalchemyAccountsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, account_id: str) -> Account | None:
        model = self._session.scalar(
            select(AccountModel).where(AccountModel.id == account_id).with_for_update()
        )
        return AccountMapper.to_domain(model) if model is not None else None

    def find_non_deleted_by_email(self, email: str) -> Account | None:
        self._session.execute(
            text('SELECT pg_advisory_xact_lock(hashtextextended(:email, 0))'),
            {'email': email},
        )
        model = self._session.scalar(
            select(AccountModel)
            .where(
                AccountModel.email == email,
                AccountModel.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return AccountMapper.to_domain(model) if model is not None else None

    def find_many_pending_created_before(
        self,
        created_before: datetime,
        *,
        limit: int | None = None,
    ) -> list[Account]:
        statement = (
            select(AccountModel)
            .where(
                AccountModel.status == AccountStatus.PENDING_CONFIRMATION.value,
                AccountModel.created_at < created_before,
            )
            .order_by(AccountModel.created_at)
            .with_for_update(skip_locked=True)
        )
        if limit is not None:
            statement = statement.limit(limit)
        models = self._session.scalars(statement).all()
        return [AccountMapper.to_domain(model) for model in models]

    def add(self, account: Account) -> None:
        self._session.add(AccountMapper.to_model(account))
        self._session.flush()

    def add_many(self, accounts: list[Account]) -> None:
        self._session.add_all([AccountMapper.to_model(account) for account in accounts])
        self._session.flush()

    def update(self, account: Account) -> None:
        self._session.merge(AccountMapper.to_model(account))

    def remove_all(self) -> None:
        self._session.execute(delete(AccountModel))
