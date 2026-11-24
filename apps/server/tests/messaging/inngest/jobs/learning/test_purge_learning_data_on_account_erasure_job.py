# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false
import asyncio
from collections.abc import Callable, Coroutine
from unittest.mock import Mock
from typing import cast
from uuid import UUID

import pytest
from inngest import NonRetriableError

from shifu.learning.core.use_cases import PurgeLearningDataForAccountUseCase
from shifu.learning.messaging.inngest.jobs import (
    PurgeLearningDataOnAccountErasureJob,
)
from shifu.shared.core.interfaces import (
    AccountErasureAcknowledgementProvider,
    AccountErasureTargetProvider,
)

_ERASURE_ID = UUID('1aadb116-a2ac-4ce8-81f4-d9e442ebd7df')
_ACCOUNT_ID = 'account-private-id'


async def _run_in_thread_immediately[T](
    function: Callable[..., T],
    *args: object,
    **kwargs: object,
) -> T:
    return function(*args, **kwargs)


def _run_without_event_loop[T](coroutine: Coroutine[object, object, T]) -> T:
    try:
        coroutine.send(None)
    except StopIteration as completed:
        return cast('T', completed.value)
    raise AssertionError('The mocked asynchronous job unexpectedly suspended')


def test_should_accept_only_an_erasure_id_payload() -> None:
    assert (
        PurgeLearningDataOnAccountErasureJob._parse_payload(
            {'erasure_id': str(_ERASURE_ID)}
        )
        == _ERASURE_ID
    )

    for payload in (
        {},
        {'erasure_id': 'not-a-uuid'},
        {'erasure_id': str(_ERASURE_ID), 'account_id': _ACCOUNT_ID},
    ):
        with pytest.raises(NonRetriableError):
            PurgeLearningDataOnAccountErasureJob._parse_payload(payload)


def test_should_purge_and_acknowledge_only_after_learning_purge_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(asyncio, 'to_thread', _run_in_thread_immediately)
    target_provider = Mock(spec=AccountErasureTargetProvider)
    target_provider.resolve_account_id.return_value = _ACCOUNT_ID
    acknowledgement_provider = Mock(spec=AccountErasureAcknowledgementProvider)
    use_case = Mock(spec=PurgeLearningDataForAccountUseCase)

    result = _run_without_event_loop(
        PurgeLearningDataOnAccountErasureJob._purge_and_acknowledge(
            _ERASURE_ID,
            use_case,
            target_provider,
            acknowledgement_provider,
        )
    )

    assert result is None
    target_provider.resolve_account_id.assert_called_once_with(_ERASURE_ID)
    use_case.execute.assert_called_once_with(_ACCOUNT_ID)
    acknowledgement_provider.acknowledge.assert_called_once_with(
        _ERASURE_ID,
        'learning',
    )


def test_should_noop_when_erasure_is_no_longer_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(asyncio, 'to_thread', _run_in_thread_immediately)
    target_provider = Mock(spec=AccountErasureTargetProvider)
    target_provider.resolve_account_id.return_value = None
    acknowledgement_provider = Mock(spec=AccountErasureAcknowledgementProvider)
    use_case = Mock(spec=PurgeLearningDataForAccountUseCase)

    _run_without_event_loop(
        PurgeLearningDataOnAccountErasureJob._purge_and_acknowledge(
            _ERASURE_ID,
            use_case,
            target_provider,
            acknowledgement_provider,
        )
    )

    use_case.execute.assert_not_called()
    acknowledgement_provider.acknowledge.assert_not_called()


def test_should_not_acknowledge_when_learning_purge_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(asyncio, 'to_thread', _run_in_thread_immediately)
    target_provider = Mock(spec=AccountErasureTargetProvider)
    target_provider.resolve_account_id.return_value = _ACCOUNT_ID
    acknowledgement_provider = Mock(spec=AccountErasureAcknowledgementProvider)
    use_case = Mock(spec=PurgeLearningDataForAccountUseCase)
    use_case.execute.side_effect = RuntimeError('database unavailable')

    with pytest.raises(RuntimeError, match='database unavailable'):
        _run_without_event_loop(
            PurgeLearningDataOnAccountErasureJob._purge_and_acknowledge(
                _ERASURE_ID,
                use_case,
                target_provider,
                acknowledgement_provider,
            )
        )

    acknowledgement_provider.acknowledge.assert_not_called()
