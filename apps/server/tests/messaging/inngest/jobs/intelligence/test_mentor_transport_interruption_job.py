"""External model transport failures cannot change the local-only response."""

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from shifu.intelligence.database.sqlalchemy.models import (
    MentorMessageModel,
    MentorResponseAttemptModel,
    MentorResponseEventModel,
)
from tests.fixtures.mentor_job_fixture import (
    _ControlledInference,  # pyright: ignore[reportPrivateUsage] - Reuse the registered-job harness.
    publish_and_wait,
    seed_request,
    controlled_mentor_endpoint as controlled_mentor_endpoint,
    inngest_app_target as inngest_app_target,
    prepared_mentor_index as prepared_mentor_index,
)

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture


@pytest.mark.usefixtures('prepared_mentor_index')
class TestMentorTransportInterruptionJob:
    def test_local_response_never_uses_external_model_transport(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        _, learner_id, attempt_id = seed_request(
            inngest_fixture, 'Como organizar meus estudos?'
        )

        publish_and_wait(inngest_fixture, attempt_id, 'completed')

        assert state.requests == []
        assert all(row['used_tokens'] == 0 for row in state.accounting_requests)
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.status == 'completed'
            assert attempt.generation_keys == []
            assert all(
                receipt['used_tokens'] == 0 for receipt in attempt.usage_calls or []
            )
            reply = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id,
                )
            )
            assert reply is not None and reply.content.strip()
            events = session.scalars(
                select(MentorResponseEventModel).where(
                    MentorResponseEventModel.attempt_id == attempt_id
                )
            ).all()
            assert any(event.kind == 'completed' for event in events)
            assert not any(event.kind == 'failed' for event in events)
            assert not any(
                event.kind == 'block'
                and (event.block_key or '').startswith('generated-')
                for event in events
            )
