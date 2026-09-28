from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlencode

from shifu.communication.core.domain.enums import (
    CommunicationChannel,
    CommunicationType,
)
from shifu.communication.core.domain.structures import (
    CommunicationRequest,
    MessageTemplateValues,
)
from shifu.communication.core.use_cases import QueueCommunicationUseCase
from shifu.identity.core.domain.enums import ActionTokenDeliveryQueueStatus
from shifu.identity.core.interfaces import (
    PasswordRecoveryDeliveryRequest,
    PasswordRecoveryDeliveryResult,
)

if TYPE_CHECKING:
    from shifu.communication.core.interfaces import (
        CommunicationDatabase,
        SecretEnvelopeProvider,
    )
    from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class PasswordRecoveryWorkflow:
    """Compose Identity recovery output with Communication adapters."""

    def __init__(
        self,
        communication_database: CommunicationDatabase,
        id_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        secret_envelope_provider: SecretEnvelopeProvider,
        action_origin: str,
    ) -> None:
        self._queue = QueueCommunicationUseCase(
            communication_database=communication_database,
            id_provider=id_provider,
            clock_provider=clock_provider,
            secret_envelope_provider=secret_envelope_provider,
        )
        self._action_origin = action_origin.rstrip('/')

    def queue(
        self,
        request: PasswordRecoveryDeliveryRequest,
    ) -> PasswordRecoveryDeliveryResult:
        try:
            self._queue.execute(
                CommunicationRequest(
                    communication_id=request.communication_id,
                    identity_action_token_id=request.identity_action_token_id,
                    account_id=request.account_id,
                    type=CommunicationType.PASSWORD_RECOVERY,
                    channel=CommunicationChannel.EMAIL,
                    recipient_email=request.recipient_email,
                    recipient_name=None,
                    message_values=MessageTemplateValues(
                        action_url=self._recovery_url(request.recovery_token),
                        expires_at=request.expires_at,
                    ),
                    idempotency_key=request.communication_id,
                    expires_at=request.expires_at,
                )
            )
        except Exception:  # noqa: BLE001 - queue failure is a safe delivery state.
            return PasswordRecoveryDeliveryResult(
                status=ActionTokenDeliveryQueueStatus.DELIVERY_UNAVAILABLE
            )
        return PasswordRecoveryDeliveryResult(
            status=ActionTokenDeliveryQueueStatus.QUEUED
        )

    def _recovery_url(self, token: str) -> str:
        return f'{self._action_origin}/reset-password?{urlencode({"token": token})}'
