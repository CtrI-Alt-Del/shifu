import asyncio
from collections.abc import Mapping
from typing import ClassVar, cast
from uuid import UUID

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent

from shifu.identity.core.domain.events import AccountErasureRequestedEvent
from shifu.identity.core.use_cases import (
    CloseBffIdentityForAccountErasureUseCase,
)
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
from shifu.shared.messaging.inngest.job_lifecycle_telemetry import (
    job_lifecycle_telemetry,
)


class CloseBffIdentityOnAccountErasureJob:
    """Durably retry the Better Auth cleanup over the authenticated BFF route."""

    FUNCTION_ID: ClassVar[str] = 'identity-close-bff-on-account-erasure'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: CloseBffIdentityForAccountErasureUseCase,
        *,
        telemetry_provider: TelemetryProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=CloseBffIdentityOnAccountErasureJob.FUNCTION_ID,
            trigger=TriggerEvent(
                event=AccountErasureRequestedEvent.EVENT_NAME,
            ),
            retries=3,
        )
        @job_lifecycle_telemetry(
            telemetry_provider,
            function_id=CloseBffIdentityOnAccountErasureJob.FUNCTION_ID,
            max_attempts=4,
        )
        async def _(context: Context) -> None:
            data = cast('Mapping[str, object]', dict(context.event.data))
            erasure_id = CloseBffIdentityOnAccountErasureJob._parse_erasure_id(data)

            async def close_identity(erasure_id: UUID) -> None:
                await asyncio.to_thread(use_case.execute, erasure_id)

            await context.step.run(
                'close_bff_identity',
                close_identity,
                erasure_id,
            )

        return _

    @staticmethod
    def _parse_erasure_id(data: Mapping[str, object]) -> UUID:
        value = data.get('erasure_id')
        if (
            set(data) != {'erasure_id'}
            or not isinstance(value, str)
            or not value.strip()
        ):
            raise NonRetriableError(
                'Account erasure event must contain only erasure_id'
            )
        try:
            return UUID(value)
        except ValueError as error:
            raise NonRetriableError('Invalid account erasure id') from error
