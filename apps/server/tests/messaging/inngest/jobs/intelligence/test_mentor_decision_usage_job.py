"""Local-only Mentor answers do not invoke or account for commercial models."""

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from shifu.intelligence.database.sqlalchemy.models import (
    MentorMessageModel,
    MentorResponseAttemptModel,
)
from tests.messaging.inngest.jobs.intelligence.test_answer_mentor_message_job import (
    _publish_and_wait,  # pyright: ignore[reportPrivateUsage] - Shared native job harness.
    _seed_request,  # pyright: ignore[reportPrivateUsage] - Shared native job harness.
    controlled_mentor_endpoint as controlled_mentor_endpoint,
    inngest_app_target as inngest_app_target,
    prepared_mentor_index as prepared_mentor_index,
)

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture
    from tests.messaging.inngest.jobs.intelligence.test_answer_mentor_message_job import (
        _ControlledInference,  # pyright: ignore[reportPrivateUsage] - Shared native job harness.
    )


class TestMentorDecisionUsageJob:
    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_registered_local_reply_is_deterministic_without_model_usage(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: 'tuple[_ControlledInference, str]',
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        replies: list[str] = []

        for _ in range(2):
            _, learner_id, attempt_id = _seed_request(
                inngest_fixture, 'Como organizar meus estudos?'
            )
            _publish_and_wait(inngest_fixture, attempt_id, 'completed')
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
                assert reply is not None
                replies.append(reply.content)

        assert replies[0] == replies[1]
        assert state.requests == []
        assert all(row['used_tokens'] == 0 for row in state.accounting_requests)
