from datetime import UTC, datetime
from unittest.mock import create_autospec
from uuid import UUID

from shifu.communication.core.domain.enums import CommunicationType
from shifu.communication.core.domain.structures import (
    AccountErasureOperationalAlertValues,
)
from shifu.communication.core.use_cases import (
    QueueAccountErasureOperationalAlertUseCase,
    QueueCommunicationUseCase,
)


class TestQueueAccountErasureOperationalAlertUseCase:
    def test_should_queue_fixed_incident_without_account_or_action_token(self) -> None:
        queue_communication = create_autospec(QueueCommunicationUseCase, instance=True)
        subject = QueueAccountErasureOperationalAlertUseCase(queue_communication)
        values = AccountErasureOperationalAlertValues(
            erasure_id=UUID('44c3e3b4-c9db-4c8a-a347-ec9109f69b62'),
            module='learning',
            failure_code='erasure_deadline_exceeded',
            closed_at=datetime(2026, 11, 20, 14, 0, tzinfo=UTC),
            due_at=datetime(2026, 11, 21, 14, 0, tzinfo=UTC),
        )

        subject.execute(values, UUID('2c6903ba-f5bd-4f14-9f6d-8849c16371a7'))

        request = queue_communication.execute.call_args.args[0]
        assert len(request.communication_id) == 26
        assert request.idempotency_key == (
            'account-erasure-alert:2c6903ba-f5bd-4f14-9f6d-8849c16371a7'
        )
        assert request.identity_action_token_id is None
        assert request.account_id is None
        assert request.type is CommunicationType.ACCOUNT_ERASURE_ALERT
        assert request.recipient_email == 'shifu.ctrlaltdel@gmail.com'
        assert request.message_values is values

    def test_should_keep_communication_identity_stable_for_same_incident(self) -> None:
        queue_communication = create_autospec(QueueCommunicationUseCase, instance=True)
        subject = QueueAccountErasureOperationalAlertUseCase(queue_communication)
        values = AccountErasureOperationalAlertValues(
            erasure_id=UUID('44c3e3b4-c9db-4c8a-a347-ec9109f69b62'),
            module='learning',
            failure_code='erasure_deadline_exceeded',
            closed_at=datetime(2026, 11, 20, 14, 0, tzinfo=UTC),
            due_at=datetime(2026, 11, 21, 14, 0, tzinfo=UTC),
        )
        incident_id = UUID('2c6903ba-f5bd-4f14-9f6d-8849c16371a7')

        subject.execute(values, incident_id)
        first_id = queue_communication.execute.call_args.args[0].communication_id
        subject.execute(values, incident_id)
        second_id = queue_communication.execute.call_args.args[0].communication_id

        assert first_id == second_id
