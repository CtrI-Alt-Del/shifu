from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import Mock, create_autospec, patch
from uuid import UUID

import pytest
from inngest import NonRetriableError

from shifu.intelligence.messaging.inngest.jobs import (
    PurgeIntelligenceOnAccountErasureJob,
)
from shifu.shared.core.interfaces import (
    AccountErasureAcknowledgementProvider,
    AccountErasureTargetProvider,
)
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine

    from inngest import Context, Inngest

    from shifu.intelligence.core.use_cases import (
        PurgeAiQuotaForAccountUseCase,
        PurgeLearnerMemoriesForAccountUseCase,
        PurgeMentorActionProposalsForAccountUseCase,
        PurgeMentorAttachmentsUseCase,
        PurgeMentorSummariesForAccountUseCase,
        PurgePlanningSessionsForAccountUseCase,
    )

_ERASURE_ID = UUID('1aadb116-a2ac-4ce8-81f4-d9e442ebd7df')
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
    attachments: PurgeMentorAttachmentsUseCase,
    summaries: PurgeMentorSummariesForAccountUseCase,
    memories: PurgeLearnerMemoriesForAccountUseCase,
    proposals: PurgeMentorActionProposalsForAccountUseCase,
    ai_quota: PurgeAiQuotaForAccountUseCase,
    planning_sessions: PurgePlanningSessionsForAccountUseCase,
) -> Callable[[Context], Awaitable[None]]:
    return cast(
        'Callable[[Context], Awaitable[None]]',
        PurgeIntelligenceOnAccountErasureJob.handle(
            cast('Inngest', _FakeInngest()),
            account_erasure_requested_event_name='identity/account-erasure.requested',
            account_erasure_target_provider=target_provider,
            account_erasure_acknowledgement_provider=acknowledgement_provider,
            purge_mentor_attachments_use_case=attachments,
            purge_mentor_summaries_use_case=summaries,
            purge_learner_memories_use_case=memories,
            purge_mentor_action_proposals_use_case=proposals,
            purge_ai_quota_use_case=ai_quota,
            purge_planning_sessions_use_case=planning_sessions,
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


def _use_cases() -> tuple[Mock, Mock, Mock, Mock, Mock, Mock]:
    return Mock(), Mock(), Mock(), Mock(), Mock(), Mock()


def _handler_for_mocks(
    target_provider: AccountErasureTargetProvider,
    acknowledgement_provider: AccountErasureAcknowledgementProvider,
    use_cases: tuple[Mock, Mock, Mock, Mock, Mock, Mock],
) -> Callable[[Context], Awaitable[None]]:
    attachments, summaries, memories, proposals, ai_quota, planning = use_cases
    return _handler(
        target_provider,
        acknowledgement_provider,
        cast('PurgeMentorAttachmentsUseCase', attachments),
        cast('PurgeMentorSummariesForAccountUseCase', summaries),
        cast('PurgeLearnerMemoriesForAccountUseCase', memories),
        cast('PurgeMentorActionProposalsForAccountUseCase', proposals),
        cast('PurgeAiQuotaForAccountUseCase', ai_quota),
        cast('PurgePlanningSessionsForAccountUseCase', planning),
    )


def test_handler_purges_all_owned_data_then_acknowledges_without_returning_pii() -> (
    None
):
    target_provider = create_autospec(AccountErasureTargetProvider, instance=True)
    target_provider.resolve_account_id.return_value = _ACCOUNT_ID
    acknowledgement_provider = create_autospec(
        AccountErasureAcknowledgementProvider, instance=True
    )
    use_cases = _use_cases()
    handler = _handler_for_mocks(target_provider, acknowledgement_provider, use_cases)

    _run(_invoke(handler, {'erasure_id': str(_ERASURE_ID)}))

    assert target_provider.resolve_account_id.call_count == 6
    use_cases[0].execute_for_deleted_account.assert_called_once_with(_ACCOUNT_ID)
    for use_case in use_cases[1:]:
        use_case.execute.assert_called_once_with(_ACCOUNT_ID)
    acknowledgement_provider.acknowledge.assert_called_once_with(
        _ERASURE_ID, 'intelligence'
    )


def test_handler_does_not_acknowledge_when_erasure_is_not_pending() -> None:
    target_provider = create_autospec(AccountErasureTargetProvider, instance=True)
    target_provider.resolve_account_id.return_value = None
    acknowledgement_provider = create_autospec(
        AccountErasureAcknowledgementProvider, instance=True
    )
    use_cases = _use_cases()
    handler = _handler_for_mocks(target_provider, acknowledgement_provider, use_cases)

    _run(_invoke(handler, {'erasure_id': str(_ERASURE_ID)}))

    for use_case in use_cases:
        use_case.assert_not_called()
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
    target_provider = create_autospec(AccountErasureTargetProvider, instance=True)
    acknowledgement_provider = create_autospec(
        AccountErasureAcknowledgementProvider, instance=True
    )
    handler = _handler_for_mocks(
        target_provider, acknowledgement_provider, _use_cases()
    )

    with pytest.raises(NonRetriableError):
        _run(_invoke(handler, data))
