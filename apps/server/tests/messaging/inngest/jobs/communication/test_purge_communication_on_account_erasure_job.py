"""Real-runtime coverage for Communication account-erasure purging."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from shifu.communication.core.domain.events import (
    CommunicationDeliveryStateChangedEvent,
    CommunicationQueuedEvent,
)
from shifu.communication.database.sqlalchemy.models import (
    CommunicationModel,
    DeliveryAttemptModel,
)
from shifu.identity.database.sqlalchemy.models import (
    AccountErasureModel,
    AccountErasureParticipantModel,
)
from shifu.shared.database.sqlalchemy.models import EventModel
from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from tests.fixtures.telemetry_boundary_fixture import telemetry_inngest_app_target

inngest_app_target = telemetry_inngest_app_target


if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture


class TestPurgeCommunicationOnAccountErasureJob:
    def test_registered_erasure_event_purges_owned_rows_and_acknowledges(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        erasure_id = uuid4()
        id_provider = IdProviderFaker()
        account_id = id_provider.generate()
        other_account_id = id_provider.generate()
        communication_id = id_provider.generate()
        other_communication_id = id_provider.generate()
        attempt_id = id_provider.generate()
        other_attempt_id = id_provider.generate()
        queued_event_id = id_provider.generate()
        state_event_id = id_provider.generate()
        other_event_id = id_provider.generate()
        now = datetime.now(UTC)

        with inngest_fixture.inspection_session() as session:
            session.add(
                AccountErasureModel(
                    erasure_id=erasure_id,
                    account_id=account_id,
                    status='pending',
                    closed_at=now,
                    due_at=now + timedelta(hours=24),
                )
            )
            session.add_all(
                [
                    AccountErasureParticipantModel(
                        erasure_id=erasure_id,
                        participant=participant,
                        status='pending',
                    )
                    for participant in (
                        'identity-bff',
                        'learning',
                        'intelligence',
                        'gamification',
                        'communication',
                    )
                ]
            )
            session.add_all(
                [
                    _communication(
                        communication_id,
                        account_id,
                        now,
                    ),
                    _communication(
                        other_communication_id,
                        other_account_id,
                        now,
                    ),
                ]
            )
            session.add_all(
                [
                    DeliveryAttemptModel(
                        id=attempt_id,
                        communication_id=communication_id,
                        attempt_number=1,
                        status='failed',
                        attempted_at=now,
                    ),
                    DeliveryAttemptModel(
                        id=other_attempt_id,
                        communication_id=other_communication_id,
                        attempt_number=1,
                        status='failed',
                        attempted_at=now,
                    ),
                ]
            )
            session.add_all(
                [
                    _outbox_event(
                        queued_event_id,
                        CommunicationQueuedEvent.NAME,
                        communication_id,
                        now,
                    ),
                    _outbox_event(
                        state_event_id,
                        CommunicationDeliveryStateChangedEvent.NAME,
                        communication_id,
                        now,
                    ),
                    _outbox_event(
                        other_event_id,
                        CommunicationQueuedEvent.NAME,
                        other_communication_id,
                        now,
                    ),
                ]
            )
            session.commit()

        event_id = id_provider.generate()
        inngest_fixture.publish(
            'identity/account-erasure.requested',
            {'erasure_id': str(erasure_id)},
            event_id,
        )
        inngest_fixture.wait_for_log(
            f'"event":"job.completed","event_id":"{event_id}"',
            timeout=90,
        )

        with inngest_fixture.inspection_session() as session:
            assert session.get(CommunicationModel, communication_id) is None
            assert session.get(DeliveryAttemptModel, attempt_id) is None
            assert session.get(EventModel, queued_event_id) is None
            assert session.get(EventModel, state_event_id) is None
            assert session.get(CommunicationModel, other_communication_id) is not None
            assert session.get(DeliveryAttemptModel, other_attempt_id) is not None
            assert session.get(EventModel, other_event_id) is not None
            participant = session.get(
                AccountErasureParticipantModel,
                (erasure_id, 'communication'),
            )
            assert participant is not None
            assert participant.status == 'acknowledged'


def _communication(
    communication_id: str,
    account_id: str,
    created_at: datetime,
) -> CommunicationModel:
    return CommunicationModel(
        id=communication_id,
        account_id=account_id,
        type='account_confirmation',
        channel='email',
        recipient_email='learner@example.com',
        recipient_name='Pessoa Aprendente',
        content={'subject': 'Confirme seu e-mail', 'html': '<p>Dados pessoais</p>'},
        status='pending',
        idempotency_key=communication_id,
        created_at=created_at,
        updated_at=created_at,
        attempt_count=1,
        encrypted_content={'ciphertext': 'secret-payload'},
    )


def _outbox_event(
    event_id: str,
    event_name: str,
    communication_id: str,
    created_at: datetime,
) -> EventModel:
    return EventModel(
        id=event_id,
        name=event_name,
        payload={'communication_id': communication_id},
        destination='unrouted',
        status='pending',
        attempts=0,
        available_at=created_at,
        created_at=created_at,
        updated_at=created_at,
    )
