from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine

from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.core.domain.errors import AccountNotActiveError
from shifu.identity.core.interfaces import IdentityDatabase
from shifu.shared.database.sqlalchemy.account_activity_scope import (
    AccountActivityScope,
)


class SqlalchemyCommunicationActivityProvider:
    """Admit account communication while the account can still receive it."""

    def __init__(self, identity_database: IdentityDatabase, engine: Engine) -> None:
        self._identity_database = identity_database
        self._engine = engine

    @contextmanager
    def activity(self, account_id: str) -> Generator[None]:
        with AccountActivityScope.shared(self._engine, account_id):
            with self._identity_database.transaction() as repositories:
                account = repositories.accounts.find_by_id(account_id)
                if account is None or account.status not in (
                    AccountStatus.ACTIVE,
                    AccountStatus.PENDING_CONFIRMATION,
                ):
                    raise AccountNotActiveError
            yield
