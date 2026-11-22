from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from hashlib import sha256
from threading import RLock
from typing import Literal

from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from shifu.shared.core.domain.errors import ServiceUnavailableError

AccountActivityMode = Literal['shared', 'exclusive']


@dataclass(slots=True)
class _AccountActivityConnection:
    account_id: str
    connection: Connection
    mode: AccountActivityMode
    advisory_key: int
    lock: RLock = field(default_factory=RLock)


_CURRENT_ACTIVITY: ContextVar[_AccountActivityConnection | None] = ContextVar(
    'shifu_account_activity_connection', default=None
)
_LOCK_TIMEOUT_MILLISECONDS = 5_000


class AccountActivityScope:
    @staticmethod
    @contextmanager
    def shared(engine: Engine, account_id: str) -> Generator[Connection]:
        with AccountActivityScope._scope(
            engine, account_id, mode='shared'
        ) as connection:
            yield connection

    @staticmethod
    @contextmanager
    def exclusive(engine: Engine, account_id: str) -> Generator[Connection]:
        with AccountActivityScope._scope(
            engine, account_id, mode='exclusive'
        ) as connection:
            yield connection

    @staticmethod
    def current_connection(engine: Engine) -> Connection | None:
        current = _CURRENT_ACTIVITY.get()
        if current is None:
            return None
        if current.connection.engine.url != engine.url:
            raise RuntimeError('Account activity cannot cross database engines')
        return current.connection

    @staticmethod
    def current_context() -> _AccountActivityConnection | None:
        return _CURRENT_ACTIVITY.get()

    @staticmethod
    def bind_context(
        context: _AccountActivityConnection,
    ) -> Token[_AccountActivityConnection | None]:
        return _CURRENT_ACTIVITY.set(context)

    @staticmethod
    def reset_context(token: Token[_AccountActivityConnection | None]) -> None:
        _CURRENT_ACTIVITY.reset(token)

    @staticmethod
    @contextmanager
    def serialize_session_use(
        connection: Connection | None,
    ) -> Generator[None]:
        current = _CURRENT_ACTIVITY.get()
        if current is None or current.connection is not connection:
            yield
            return
        with current.lock:
            yield

    @staticmethod
    @contextmanager
    def _scope(
        engine: Engine,
        account_id: str,
        *,
        mode: AccountActivityMode,
    ) -> Generator[Connection]:
        if not account_id.strip():
            raise ValueError('account_id must not be empty')

        current = _CURRENT_ACTIVITY.get()
        if current is not None:
            connection = AccountActivityScope._nested_connection(
                current,
                engine=engine,
                account_id=account_id,
                mode=mode,
            )
            yield connection
            return

        with AccountActivityScope._owned_scope(
            engine, account_id, mode=mode
        ) as connection:
            yield connection

    @staticmethod
    def _nested_connection(
        current: _AccountActivityConnection,
        *,
        engine: Engine,
        account_id: str,
        mode: AccountActivityMode,
    ) -> Connection:
        if current.account_id != account_id:
            raise RuntimeError('Nested account activity cannot change accounts')
        if current.mode == 'shared' and mode == 'exclusive':
            raise RuntimeError('Account activity lock cannot be upgraded')
        if current.connection.engine.url != engine.url:
            raise RuntimeError('Account activity cannot cross database engines')
        return current.connection

    @staticmethod
    @contextmanager
    def _owned_scope(
        engine: Engine,
        account_id: str,
        *,
        mode: AccountActivityMode,
    ) -> Generator[Connection]:
        connection = AccountActivityScope._connect(engine)
        advisory_key = AccountActivityScope._advisory_key(account_id)
        lock_function, unlock_function = AccountActivityScope._lock_functions(mode)
        state = _AccountActivityConnection(
            account_id=account_id,
            connection=connection,
            mode=mode,
            advisory_key=advisory_key,
        )
        token: Token[_AccountActivityConnection | None] | None = None
        locked = False
        try:
            AccountActivityScope._acquire_session_lock(
                connection,
                advisory_key=advisory_key,
                lock_function=lock_function,
            )
            locked = True
            token = _CURRENT_ACTIVITY.set(state)
            yield connection
        finally:
            if token is not None:
                _CURRENT_ACTIVITY.reset(token)
            AccountActivityScope._release_session_lock(
                connection,
                advisory_key=advisory_key,
                unlock_function=unlock_function,
                locked=locked,
            )

    @staticmethod
    def _connect(engine: Engine) -> Connection:
        try:
            return engine.connect()
        except SQLAlchemyError as error:
            raise ServiceUnavailableError(
                message='A conta está ocupada. Tente novamente.'
            ) from error

    @staticmethod
    def _lock_functions(mode: AccountActivityMode) -> tuple[str, str]:
        lock_function = (
            'pg_advisory_lock_shared' if mode == 'shared' else 'pg_advisory_lock'
        )
        unlock_function = (
            'pg_advisory_unlock_shared' if mode == 'shared' else 'pg_advisory_unlock'
        )
        return lock_function, unlock_function

    @staticmethod
    def _acquire_session_lock(
        connection: Connection,
        *,
        advisory_key: int,
        lock_function: str,
    ) -> None:
        try:
            connection.execute(
                text(f"SET lock_timeout = '{_LOCK_TIMEOUT_MILLISECONDS}ms'")
            )
            connection.commit()
            connection.execute(
                text(f'SELECT {lock_function}(:advisory_key)'),
                {'advisory_key': advisory_key},
            )
            connection.commit()
        except DBAPIError as error:
            raise ServiceUnavailableError(
                message='A conta está ocupada. Tente novamente.'
            ) from error

    @staticmethod
    def _release_session_lock(
        connection: Connection,
        *,
        advisory_key: int,
        unlock_function: str,
        locked: bool,
    ) -> None:
        try:
            if connection.in_transaction():
                connection.rollback()
            if locked and not connection.closed and not connection.invalidated:
                connection.execute(
                    text(f'SELECT {unlock_function}(:advisory_key)'),
                    {'advisory_key': advisory_key},
                )
                connection.commit()
            if not connection.closed and not connection.invalidated:
                connection.execute(text('RESET lock_timeout'))
                connection.commit()
        except SQLAlchemyError:
            connection.invalidate()
        finally:
            connection.close()

    @staticmethod
    def _advisory_key(account_id: str) -> int:
        digest = sha256(f'shifu:account-activity:v1:{account_id}'.encode()).digest()
        return int.from_bytes(digest[:8], byteorder='big', signed=True)
