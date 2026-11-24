from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import create_autospec
from uuid import UUID

import pytest
from inngest import NonRetriableError

from shifu.identity.core.use_cases import (
    CloseBffIdentityForAccountErasureUseCase,
)
from shifu.identity.messaging.inngest.jobs import (
    CloseBffIdentityOnAccountErasureJob,
)
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine

    from inngest import Context, Inngest

_ERASURE_ID = UUID('1aadb116-a2ac-4ce8-81f4-d9e442ebd7df')


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
    use_case: CloseBffIdentityForAccountErasureUseCase,
) -> Callable[[Context], Awaitable[None]]:
    return cast(
        'Callable[[Context], Awaitable[None]]',
        CloseBffIdentityOnAccountErasureJob.handle(
            cast('Inngest', _FakeInngest()),
            use_case,
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
    from unittest.mock import patch

    try:
        with patch('asyncio.to_thread', new=_run_in_thread_immediately):
            awaitable.send(None)
    except StopIteration:
        return
    finally:
        awaitable.close()
    raise AssertionError('The fake Inngest handler unexpectedly suspended.')


def test_handler_closes_only_the_opaque_pending_erasure() -> None:
    use_case = create_autospec(
        CloseBffIdentityForAccountErasureUseCase,
        instance=True,
    )
    handler = _handler(use_case)

    _run(_invoke(handler, {'erasure_id': str(_ERASURE_ID)}))

    use_case.execute.assert_called_once_with(_ERASURE_ID)


@pytest.mark.parametrize(
    'data',
    [
        {},
        {'erasure_id': 'not-a-uuid'},
        {'erasure_id': str(_ERASURE_ID), 'account_id': 'private-account-id'},
    ],
)
def test_handler_rejects_invalid_or_pii_bearing_event(data: dict[str, object]) -> None:
    use_case = create_autospec(
        CloseBffIdentityForAccountErasureUseCase,
        instance=True,
    )
    handler = _handler(use_case)

    with pytest.raises(NonRetriableError):
        _run(_invoke(handler, data))

    use_case.execute.assert_not_called()
