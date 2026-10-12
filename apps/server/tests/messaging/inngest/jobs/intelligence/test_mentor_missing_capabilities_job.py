"""Registered native-job authorization and local identity behavior."""

import os
from collections.abc import Iterator
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine, select

from shifu.app import FastAPIApp
from shifu.fakers.identity.entities.account_faker import AccountFaker
from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.providers.identity_mentor_access_provider import (
    IdentityMentorAccessProvider,
)
from shifu.intelligence.database.sqlalchemy.models import (
    MentorMessageModel,
    MentorResponseAttemptModel,
    MentorResponseEventModel,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.messaging.inngest.jobs.intelligence.test_answer_mentor_message_job import (
    _publish_and_wait,  # pyright: ignore[reportPrivateUsage] - Existing native harness.
    _seed_request,  # pyright: ignore[reportPrivateUsage] - Existing native harness.
    controlled_mentor_endpoint as controlled_mentor_endpoint,
    create_mentor_test_app,
    prepared_mentor_index as prepared_mentor_index,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from shifu.shared.core.interfaces import MentorContextProvider
    from shifu.intelligence.core.interfaces import (
        AnswerMentorMessageWorkflow,
        MentorRouteProvider,
        MentorTelemetryProvider,
    )
    from tests.fixtures.inngest_fixture import InngestFixture
    from tests.messaging.inngest.jobs.intelligence.test_answer_mentor_message_job import (
        _ControlledInference,  # pyright: ignore[reportPrivateUsage] - Existing native harness.
    )


def create_missing_capabilities_app() -> FastAPI:
    original_register = FastAPIApp.register

    def register(database_engine: 'Engine | None' = None, **kwargs: object) -> FastAPI:
        assert database_engine is not None
        return original_register(
            database_engine,
            answer_mentor_message_workflow=cast(
                'AnswerMentorMessageWorkflow',
                kwargs['answer_mentor_message_workflow'],
            ),
            mentor_access_provider=IdentityMentorAccessProvider(
                SqlalchemyIdentityDatabase(database_engine)
            ),
            mentor_route_provider=cast(
                'MentorRouteProvider', kwargs['mentor_route_provider']
            ),
            mentor_telemetry_provider=cast(
                'MentorTelemetryProvider', kwargs['mentor_telemetry_provider']
            ),
            mentor_context_provider=cast(
                'MentorContextProvider | None', kwargs.get('mentor_context_provider')
            ),
        )

    # Preserve the actual job and adapters while using Identity's real account database.
    with patch.object(FastAPIApp, 'register', side_effect=register):
        return create_mentor_test_app()


@pytest.fixture(scope='session')
def inngest_app_target(
    controlled_mentor_endpoint: 'tuple[_ControlledInference, str]',
) -> Iterator[tuple[str, bool]]:
    del controlled_mentor_endpoint
    previous = os.environ.get('MENTOR_TELEMETRY_ENABLED')
    os.environ['MENTOR_TELEMETRY_ENABLED'] = 'false'
    try:
        yield (
            'tests.messaging.inngest.jobs.intelligence.test_mentor_missing_capabilities_job:create_missing_capabilities_app',
            True,
        )
    finally:
        if previous is None:
            os.environ.pop('MENTOR_TELEMETRY_ENABLED', None)
        else:
            os.environ['MENTOR_TELEMETRY_ENABLED'] = previous


@pytest.mark.usefixtures('prepared_mentor_index')
class TestMentorInvalidIdentityAccessJob:
    @pytest.mark.parametrize(
        'mode',
        ['missing_account', 'inactive', 'stale'],
    )
    def test_registered_native_job_fails_closed_when_identity_access_is_invalid(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: 'tuple[_ControlledInference, str]',
        mode: str,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset(mode)
        learner_id, attempt_id = _seed_identity_request(inngest_fixture, mode)
        _publish_and_wait(inngest_fixture, attempt_id, 'failed')

        assert state.requests == []
        assert state.accounting_requests == []
        assert state.effective_usage == {}
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None
            assert attempt.status == 'failed'
            assert all(
                receipt['used_tokens'] == 0
                for receipt in attempt.usage_calls or []
            )
            assert (
                session.scalars(
                    select(MentorMessageModel).where(
                        MentorMessageModel.in_reply_to_message_id == learner_id
                    )
                ).all()
                == []
            )
            events = session.scalars(
                select(MentorResponseEventModel).where(
                    MentorResponseEventModel.attempt_id == attempt_id
                )
            ).all()
            if mode in {'missing_account', 'inactive', 'stale'}:
                # A failed private response cannot expose events after access is lost.
                assert events == []
            else:
                assert any(event.kind == 'failed' for event in events)
                assert not any(event.kind == 'completed' for event in events)
                assert not any(
                    event.kind == 'block'
                    and event.block_key is not None
                    and event.block_key.startswith('generated-')
                    for event in events
                )


def _seed_identity_request(fixture: 'InngestFixture', mode: str) -> tuple[str, str]:
    account_id = SystemIdentifierProvider().generate()
    if mode != 'missing_account':
        engine = create_engine(fixture.database_url)
        try:
            with SqlalchemyIdentityDatabase(engine).transaction() as repositories:
                repositories.accounts.add(
                    AccountFaker.fake(
                        id=account_id,
                        status=AccountStatus.PENDING_CONFIRMATION
                        if mode == 'inactive'
                        else AccountStatus.ACTIVE,
                        access_version=2 if mode == 'stale' else 1,
                    )
                )
        finally:
            engine.dispose()
    _, learner_id, attempt_id = _seed_request(
        fixture, 'Como organizar meus estudos?', account_id=account_id
    )
    with fixture.inspection_session() as session:
        attempt = session.get(MentorResponseAttemptModel, attempt_id)
        assert attempt is not None
        attempt.access_revision = '1'
        session.commit()
    return learner_id, attempt_id


@pytest.mark.usefixtures('prepared_mentor_index')
class TestMentorIdentityAccessJob:
    def test_registered_native_job_completes_with_identity_without_model_calls(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: 'tuple[_ControlledInference, str]',
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        learner_id, attempt_id = _seed_identity_request(inngest_fixture, 'approve')
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert state.requests == []
        assert state.accounting_requests == []
        assert state.effective_usage == {}
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.status == 'completed'
            assert attempt.generation_keys == []
            assert all(
                receipt['used_tokens'] == 0
                for receipt in attempt.usage_calls or []
            )
            messages = session.scalars(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            ).all()
            assert len(messages) == 1 and messages[0].content.strip()
            assert 'Ainda não encontrei uma resposta local confiável' in messages[0].content
            events = session.scalars(
                select(MentorResponseEventModel).where(
                    MentorResponseEventModel.attempt_id == attempt_id
                )
            ).all()
            assert any(event.kind == 'completed' for event in events)
            assert not any(
                event.kind == 'block'
                and event.block_key is not None
                and event.block_key.startswith('generated-')
                for event in events
            )
            assert all(event.kind != 'failed' for event in events)
