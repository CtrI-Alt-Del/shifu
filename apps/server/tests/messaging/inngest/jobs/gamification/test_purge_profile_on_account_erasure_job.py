from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import Mock, create_autospec, patch
from uuid import UUID

import pytest
from inngest import NonRetriableError

from shifu.gamification.messaging.inngest.jobs import (
    PurgeProfileOnAccountErasureJob,
)
from shifu.shared.core.interfaces import (
    AccountErasureAcknowledgementProvider,
    AccountErasureTargetProvider,
)
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine

    from inngest import Context, Inngest

    from shifu.gamification.core.use_cases import DeleteGamificationProfileUseCase

_ERASURE_ID = UUID('fd883ee9-b507-4b86-a28c-f0b7d1336fab')
_ACCOUNT_ID = 'account-private-id'


class _FakeInngest:
    def create_function(
        self, **_options: object
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def register(handler: Callable[..., Any]) -> Callable[..., Any]:
            return handler

        return register


class _FakeStep:
    async def run(self, _name: str, function: Callable[..., Any], *args: Any) -> Any:
        result = function(*args)
        if inspect.isawaitable(result):
            return await result
        return result


def _handler(
    target_provider: AccountErasureTargetProvider,
    acknowledgement_provider: AccountErasureAcknowledgementProvider,
    use_case: DeleteGamificationProfileUseCase,
) -> Callable[[Context], Awaitable[None]]:
    return cast(
        'Callable[[Context], Awaitable[None]]',
        PurgeProfileOnAccountErasureJob.handle(
            cast('Inngest', _FakeInngest()),
            use_case,
            account_erasure_requested_event_name='identity/account-erasure.requested',
            account_erasure_target_provider=target_provider,
            account_erasure_acknowledgement_provider=acknowledgement_provider,
            telemetry_provider=create_autospec(TelemetryProvider, instance=True),
        ),
    )


async def _invoke(
    handler: Callable[[Context], Awaitable[None]], data: dict[str, object]
) -> None:
    context = cast(
        'Context',
        SimpleNamespace(
            event=SimpleNamespace(data=data, id='event-1'),
            run_id='run-1',
            attempt=0,
            step=_FakeStep(),
        ),
    )
    await handler(context)


async def _run_in_thread_immediately[T](
    function: Callable[..., T], *args: Any, **kwargs: Any
) -> T:
    return function(*args, **kwargs)


def _run(awaitable: Coroutine[Any, Any, None]) -> None:
    try:
        with patch('asyncio.to_thread', new=_run_in_thread_immediately):
            awaitable.send(None)
    except StopIteration:
        return
    finally:
        awaitable.close()
    raise AssertionError('The fake Inngest handler unexpectedly suspended.')


def test_handler_resolves_account_purges_and_acknowledges_without_returning_pii() -> (
    None
):
    target_provider = create_autospec(AccountErasureTargetProvider, instance=True)
    target_provider.resolve_account_id.return_value = _ACCOUNT_ID
    acknowledgement_provider = create_autospec(
        AccountErasureAcknowledgementProvider, instance=True
    )
    use_case = Mock()
    handler = _handler(target_provider, acknowledgement_provider, cast('Any', use_case))

    _run(_invoke(handler, {'erasure_id': str(_ERASURE_ID)}))

    target_provider.resolve_account_id.assert_called_once_with(_ERASURE_ID)
    use_case.execute.assert_called_once_with(_ACCOUNT_ID)
    acknowledgement_provider.acknowledge.assert_called_once_with(
        _ERASURE_ID, 'gamification'
    )


def test_handler_does_not_acknowledge_when_erasure_is_not_pending() -> None:
    target_provider = create_autospec(AccountErasureTargetProvider, instance=True)
    target_provider.resolve_account_id.return_value = None
    acknowledgement_provider = create_autospec(
        AccountErasureAcknowledgementProvider, instance=True
    )
    use_case = Mock()
    handler = _handler(target_provider, acknowledgement_provider, cast('Any', use_case))

    _run(_invoke(handler, {'erasure_id': str(_ERASURE_ID)}))

    use_case.execute.assert_not_called()
    acknowledgement_provider.acknowledge.assert_not_called()


@pytest.mark.parametrize(
    'data',
    [
        {},
        {'erasure_id': 'not-a-uuid'},
        {'erasure_id': str(_ERASURE_ID), 'account_id': _ACCOUNT_ID},
    ],
)
def test_handler_rejects_invalid_or_pii_bearing_payloads(
    data: dict[str, object],
) -> None:
    handler = _handler(
        create_autospec(AccountErasureTargetProvider, instance=True),
        create_autospec(AccountErasureAcknowledgementProvider, instance=True),
        cast('Any', Mock()),
    )

    with pytest.raises(NonRetriableError):
        _run(_invoke(handler, data))
