from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
)
from shifu.identity.database.sqlalchemy.mappers import AccountActionTokenMapper
from shifu.identity.database.sqlalchemy.models import AccountActionTokenModel


class SqlalchemyAccountActionTokensRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_hash(self, token_hash: str) -> AccountActionToken | None:
        model = self._session.scalar(
            select(AccountActionTokenModel)
            .where(AccountActionTokenModel.token_hash == token_hash)
            .with_for_update()
        )
        return AccountActionTokenMapper.to_domain(model) if model is not None else None

    def find_by_id(self, identity_confirmation_id: str) -> AccountActionToken | None:
        model = self._session.scalar(
            select(AccountActionTokenModel)
            .where(AccountActionTokenModel.id == identity_confirmation_id)
            .with_for_update()
        )
        return AccountActionTokenMapper.to_domain(model) if model is not None else None

    def find_by_pending_handle_hash(
        self,
        pending_handle_hash: str,
    ) -> AccountActionToken | None:
        model = self._session.scalar(
            select(AccountActionTokenModel)
            .where(AccountActionTokenModel.pending_handle_hash == pending_handle_hash)
            .order_by(AccountActionTokenModel.issued_at.desc())
            .with_for_update()
        )
        return AccountActionTokenMapper.to_domain(model) if model is not None else None

    def find_latest_by_account_id_and_type(
        self,
        account_id: str,
        token_type: AccountActionTokenType,
    ) -> AccountActionToken | None:
        model = self._session.scalar(
            select(AccountActionTokenModel)
            .where(
                AccountActionTokenModel.account_id == account_id,
                AccountActionTokenModel.type == token_type.value,
            )
            .order_by(AccountActionTokenModel.issued_at.desc())
            .with_for_update()
        )
        return AccountActionTokenMapper.to_domain(model) if model is not None else None

    def find_many_by_account_id_and_type(
        self,
        account_id: str,
        token_type: AccountActionTokenType,
    ) -> list[AccountActionToken]:
        models = self._session.scalars(
            select(AccountActionTokenModel)
            .where(
                AccountActionTokenModel.account_id == account_id,
                AccountActionTokenModel.type == token_type.value,
            )
            .order_by(AccountActionTokenModel.issued_at)
            .with_for_update()
        ).all()
        return [AccountActionTokenMapper.to_domain(model) for model in models]

    def find_many_pending_by_account_id_and_type(
        self,
        account_id: str,
        token_type: AccountActionTokenType,
    ) -> list[AccountActionToken]:
        models = self._session.scalars(
            select(AccountActionTokenModel)
            .where(
                AccountActionTokenModel.account_id == account_id,
                AccountActionTokenModel.type == token_type.value,
                AccountActionTokenModel.status
                == AccountActionTokenStatus.PENDING.value,
            )
            .order_by(AccountActionTokenModel.issued_at)
            .with_for_update()
        ).all()
        return [AccountActionTokenMapper.to_domain(model) for model in models]

    def add(self, token: AccountActionToken) -> None:
        self._session.add(AccountActionTokenMapper.to_model(token))

    def add_many(self, tokens: list[AccountActionToken]) -> None:
        self._session.add_all(
            [AccountActionTokenMapper.to_model(token) for token in tokens]
        )
        self._session.flush()

    def update(self, token: AccountActionToken) -> None:
        self._session.merge(AccountActionTokenMapper.to_model(token))

    def remove_all(self) -> None:
        self._session.execute(delete(AccountActionTokenModel))
