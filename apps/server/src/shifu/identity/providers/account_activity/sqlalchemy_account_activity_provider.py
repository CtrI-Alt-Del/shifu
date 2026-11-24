import asyncio
from collections.abc import AsyncGenerator, Generator
from contextvars import Context, copy_context
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager, asynccontextmanager, contextmanager
from re import fullmatch
from types import TracebackType
from uuid import UUID

from sqlalchemy import Engine

from shifu.identity.core.domain.entities import Account
from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.core.domain.errors import AccountNotActiveError
from shifu.identity.core.interfaces import IdentityDatabase
from shifu.identity.core.domain.structures import (
    AccountExternalEffectReceiptAdmission,
)
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.errors import ConflictError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.sqlalchemy.account_activity_scope import (
    AccountActivityScope,
)

_EXTERNAL_EFFECT_OPERATION_PATTERN = r'[a-z][a-z0-9_.-]{0,119}'


async def _wait_for_completion[T](future: asyncio.Future[T]) -> T:
    """Let the work finish even when cancelled, then re-raise the cancellation."""
    try:
        return await asyncio.shield(future)
    except asyncio.CancelledError:
        if not future.done():
            # A further cancellation re-raises from here once the work is done.
            await _wait_for_completion(future)
        raise


@asynccontextmanager
async def _non_blocking_context[ContextValue](
    manager: AbstractContextManager[ContextValue],
) -> AsyncGenerator[ContextValue]:
    executor = ThreadPoolExecutor(max_workers=1)
    loop = asyncio.get_running_loop()
    activity_context: Context = copy_context()
    enter_future = loop.run_in_executor(
        executor, activity_context.run, manager.__enter__
    )
    context_token = None

    def reset_current_context() -> None:
        nonlocal context_token
        if context_token is not None:
            AccountActivityScope.reset_context(context_token)
            context_token = None

    def exit_manager(
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return activity_context.run(manager.__exit__, exc_type, exc_value, traceback)

    try:
        try:
            value = await asyncio.shield(enter_future)
        except asyncio.CancelledError as cancelled:
            try:
                await _wait_for_completion(enter_future)
            finally:
                if not enter_future.cancelled() and enter_future.exception() is None:
                    exit_future = loop.run_in_executor(
                        executor,
                        exit_manager,
                        type(cancelled),
                        cancelled,
                        cancelled.__traceback__,
                    )
                    await _wait_for_completion(exit_future)
            raise cancelled from None

        bound_activity = activity_context.run(AccountActivityScope.current_context)
        if bound_activity is not None:
            context_token = AccountActivityScope.bind_context(bound_activity)

        try:
            yield value
        except BaseException as error:
            reset_current_context()
            suppressed = await asyncio.shield(
                loop.run_in_executor(
                    executor,
                    exit_manager,
                    type(error),
                    error,
                    error.__traceback__,
                )
            )
            if not suppressed:
                raise
        else:
            reset_current_context()
            await asyncio.shield(
                loop.run_in_executor(
                    executor,
                    exit_manager,
                    None,
                    None,
                    None,
                )
            )
    finally:
        reset_current_context()
        executor.shutdown(wait=True)


class SqlalchemyAccountActivityProvider:
    def __init__(self, identity_database: IdentityDatabase, engine: Engine) -> None:
        self._identity_database = identity_database
        self._engine = engine

    @contextmanager
    def activity(
        self,
        account_id: str,
        *,
        actor: AuthenticatedUser | None = None,
        allow_pending_confirmation: bool = False,
    ) -> Generator[None]:
        with AccountActivityScope.shared(self._engine, account_id):
            with self._identity_database.transaction() as repositories:
                account = repositories.accounts.find_by_id(account_id)
                self._validate(
                    account,
                    account_id,
                    actor,
                    allow_pending_confirmation=allow_pending_confirmation,
                )
            yield

    @asynccontextmanager
    async def async_activity(
        self,
        account_id: str,
        *,
        actor: AuthenticatedUser | None = None,
        allow_pending_confirmation: bool = False,
    ) -> AsyncGenerator[None]:
        async with _non_blocking_context(
            self.activity(
                account_id,
                actor=actor,
                allow_pending_confirmation=allow_pending_confirmation,
            )
        ):
            yield

    @contextmanager
    def external_effect(
        self,
        account_id: str,
        effect_id: UUID,
        operation: str,
        *,
        allow_pending_confirmation: bool = False,
        allow_durable_result_recovery: bool = False,
    ) -> Generator[bool]:
        if fullmatch(_EXTERNAL_EFFECT_OPERATION_PATTERN, operation) is None:
            raise ValueError('operation must be a controlled lowercase identifier')
        if allow_pending_confirmation and operation != 'communication.email.send':
            raise ValueError(
                'allow_pending_confirmation is only valid for communication.email.send'
            )

        with AccountActivityScope.shared(self._engine, account_id):
            with self._identity_database.transaction() as repositories:
                account = repositories.accounts.find_by_id(account_id)
                self._validate(
                    account,
                    account_id,
                    None,
                    allow_pending_confirmation=allow_pending_confirmation,
                )
                receipt = repositories.external_effect_receipts.admit(
                    account_id,
                    effect_id,
                    operation,
                )

            with self._external_effect_receipt_scope(
                receipt,
                account_id,
                effect_id,
                operation,
                allow_durable_result_recovery=allow_durable_result_recovery,
            ) as should_run:
                yield should_run

    @contextmanager
    def _external_effect_receipt_scope(
        self,
        receipt: AccountExternalEffectReceiptAdmission,
        account_id: str,
        effect_id: UUID,
        operation: str,
        *,
        allow_durable_result_recovery: bool,
    ) -> Generator[bool]:
        if receipt.operation != operation:
            raise ConflictError('O receipt do efeito externo está em conflito.')
        if receipt.state == 'settled':
            yield False
            return
        if receipt.state in ('in_flight', 'unknown') and not receipt.is_new:
            if not allow_durable_result_recovery:
                raise ConflictError(
                    'O resultado do efeito externo ainda não foi reconciliado.'
                )
            try:
                yield False
            finally:
                with self._identity_database.transaction() as repositories:
                    repositories.external_effect_receipts.settle(account_id, effect_id)
            return
        if receipt.state != 'in_flight' or not receipt.is_new:
            raise ConflictError(
                'O resultado do efeito externo ainda não foi reconciliado.'
            )

        try:
            yield True
        except BaseException:
            with self._identity_database.transaction() as repositories:
                repositories.external_effect_receipts.mark_unknown(
                    account_id, effect_id
                )
            raise
        else:
            with self._identity_database.transaction() as repositories:
                repositories.external_effect_receipts.settle(account_id, effect_id)

    @asynccontextmanager
    async def async_external_effect(
        self,
        account_id: str,
        effect_id: UUID,
        operation: str,
        *,
        allow_pending_confirmation: bool = False,
        allow_durable_result_recovery: bool = False,
    ) -> AsyncGenerator[bool]:
        async with _non_blocking_context(
            self.external_effect(
                account_id,
                effect_id,
                operation,
                allow_pending_confirmation=allow_pending_confirmation,
                allow_durable_result_recovery=allow_durable_result_recovery,
            )
        ) as should_run:
            yield should_run

    @staticmethod
    def _validate(
        account: Account | None,
        account_id: str,
        actor: AuthenticatedUser | None,
        *,
        allow_pending_confirmation: bool = False,
    ) -> None:
        if account is None or (
            account.status is not AccountStatus.ACTIVE
            and not (
                allow_pending_confirmation
                and account.status is AccountStatus.PENDING_CONFIRMATION
            )
        ):
            raise AccountNotActiveError
        if actor is None:
            return
        if actor.account_id != account_id:
            raise AuthorizationError
        if (
            actor.account_access_version != account.access_version
            or actor.session_id is None
            or actor.token_access_version is None
            or not account.accepts_access(actor.session_id, actor.token_access_version)
        ):
            raise AuthorizationError
