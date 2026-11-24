from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine
from shifu.identity.core.interfaces import IdentityDatabaseRepositories
from shifu.identity.database.sqlalchemy.repositories import (
    SqlalchemyAccountActionTokensRepository,
    SqlalchemyAccountBrowserCapabilitiesRepository,
    SqlalchemyAccountExternalEffectReceiptsRepository,
    SqlalchemyAccountErasureRepository,
    SqlalchemyAccountsRepository,
)
from shifu.shared.core.interfaces import IdentifierProvider
from shifu.shared.database.sqlalchemy.repositories import SqlalchemyEventsRepository
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.database.sqlalchemy.account_activity_scope import (
    AccountActivityScope,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider


class SqlalchemyIdentityDatabase:
    def __init__(
        self,
        engine: Engine | None = None,
        id_provider: IdentifierProvider | None = None,
        *,
        activity_engine: Engine | None = None,
    ) -> None:
        self._engine = engine or Session.create_database_engine()
        self._activity_engine = activity_engine or self._engine
        self._id_provider: IdentifierProvider = (
            id_provider or SystemIdentifierProvider()
        )

    @contextmanager
    def transaction(self) -> Generator[IdentityDatabaseRepositories]:
        with Session.database_session(self._engine) as session:
            repositories = IdentityDatabaseRepositories(
                accounts=SqlalchemyAccountsRepository(session),
                account_action_tokens=SqlalchemyAccountActionTokensRepository(session),
                account_browser_capabilities=(
                    SqlalchemyAccountBrowserCapabilitiesRepository(session)
                ),
                external_effect_receipts=(
                    SqlalchemyAccountExternalEffectReceiptsRepository(session)
                ),
                account_erasures=SqlalchemyAccountErasureRepository(session),
                events=SqlalchemyEventsRepository(
                    session,
                    self._engine,
                    id_provider=self._id_provider,
                ),
            )
            yield repositories

    @contextmanager
    def account_closure_transaction(
        self, account_id: str
    ) -> Generator[IdentityDatabaseRepositories]:
        with (
            AccountActivityScope.exclusive(self._activity_engine, account_id),
            self.transaction() as repositories,
        ):
            yield repositories
