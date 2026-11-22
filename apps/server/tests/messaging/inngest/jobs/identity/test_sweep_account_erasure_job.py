"""Real-runtime coverage for overdue account-erasure alerts."""

from datetime import UTC, datetime, timedelta
import json
from typing import TYPE_CHECKING
from uuid import uuid4

from shifu.identity.database.sqlalchemy.models import (
    AccountErasureModel,
    AccountErasureParticipantModel,
)
from shifu.identity.database.sqlalchemy.repositories import (
    SqlalchemyAccountErasureRepository,
)
from shifu.identity.messaging.inngest.jobs.sweep_account_erasures_job import (
    SweepAccountErasuresJob,
)

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture


_PARTICIPANTS = (
    'identity-bff',
    'learning',
    'intelligence',
    'gamification',
    'communication',
)


class TestSweepAccountErasuresJob:
    def test_overdue_pending_participant_sends_sanitized_operational_alert(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        erasure_id = uuid4()
        account_id = '01JACCOUNT0000000000000001'
        now = datetime.now(UTC)
        closed_at = now - timedelta(hours=49)
        due_at = closed_at + timedelta(hours=24)
        acknowledged_at = due_at

        with inngest_fixture.inspection_session() as session:
            session.add(
                AccountErasureModel(
                    erasure_id=erasure_id,
                    account_id=account_id,
                    status='pending',
                    closed_at=closed_at,
                    due_at=due_at,
                )
            )
            session.add_all(
                [
                    AccountErasureParticipantModel(
                        erasure_id=erasure_id,
                        participant=participant,
                        status='pending'
                        if participant == 'learning'
                        else 'acknowledged',
                        acknowledged_at=(
                            None if participant == 'learning' else acknowledged_at
                        ),
                    )
                    for participant in _PARTICIPANTS
                ]
            )
            session.commit()
            overdue = SqlalchemyAccountErasureRepository(
                session
            ).find_overdue_pending_participants(as_of=now, limit=100)

        assert [
            (participant.erasure_id, participant.module) for participant in overdue
        ] == [(erasure_id, 'learning')]

        inngest_fixture.clear_mailpit()
        inngest_fixture.invoke_function(SweepAccountErasuresJob.FUNCTION_ID)
        messages = inngest_fixture.wait_for_mail_count(1, timeout=60)

        message_data = json.dumps(messages)
        assert 'shifu.ctrlaltdel@gmail.com' in message_data
        assert str(erasure_id) in message_data
        assert 'learning' in message_data
        assert 'erasure_deadline_exceeded' in message_data
        assert account_id not in message_data
