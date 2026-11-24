from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from shifu.identity.database.sqlalchemy.models import AccountBrowserCapabilityModel

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult


class SqlalchemyAccountBrowserCapabilitiesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self, *, account_id: str, capability_hash: str, created_at: datetime
    ) -> None:
        self._session.add(
            AccountBrowserCapabilityModel(
                capability_hash=capability_hash,
                account_id=account_id,
                status='active',
                created_at=created_at,
            )
        )

    def find_status_by_hash(self, capability_hash: str) -> str | None:
        return self._session.scalar(
            select(AccountBrowserCapabilityModel.status).where(
                AccountBrowserCapabilityModel.capability_hash == capability_hash
            )
        )

    def revoke_by_account_id(self, account_id: str) -> int:
        result = cast(
            'CursorResult[Any]',
            self._session.execute(
                update(AccountBrowserCapabilityModel)
                .where(
                    AccountBrowserCapabilityModel.account_id == account_id,
                    AccountBrowserCapabilityModel.status == 'active',
                )
                .values(status='revoked')
            ),
        )
        return result.rowcount or 0

    def remove_by_account_id(self, account_id: str) -> int:
        result = cast(
            'CursorResult[Any]',
            self._session.execute(
                delete(AccountBrowserCapabilityModel).where(
                    AccountBrowserCapabilityModel.account_id == account_id
                )
            ),
        )
        return result.rowcount or 0
