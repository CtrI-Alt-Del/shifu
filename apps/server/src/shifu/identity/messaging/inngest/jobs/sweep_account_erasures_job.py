"""Requeue pending erasures and expire old completed status records."""

import asyncio
from typing import ClassVar

from inngest import Context, Function, Inngest, TriggerCron

from shifu.identity.core.use_cases import RequeuePendingAccountErasuresUseCase
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
from shifu.shared.messaging.inngest.job_lifecycle_telemetry import (
    job_lifecycle_telemetry,
)


class SweepAccountErasuresJob:
    FUNCTION_ID: ClassVar[str] = 'identity-sweep-account-erasures'
    _CRON: ClassVar[str] = '*/15 * * * *'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: RequeuePendingAccountErasuresUseCase,
        *,
        telemetry_provider: TelemetryProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=SweepAccountErasuresJob.FUNCTION_ID,
            trigger=TriggerCron(cron=SweepAccountErasuresJob._CRON),
            retries=3,
        )
        @job_lifecycle_telemetry(
            telemetry_provider,
            function_id=SweepAccountErasuresJob.FUNCTION_ID,
            max_attempts=4,
        )
        async def _(context: Context) -> None:
            await context.step.run(
                'requeue_pending_erasures',
                SweepAccountErasuresJob._requeue,
                use_case,
            )

        return _

    @staticmethod
    async def _requeue(
        use_case: RequeuePendingAccountErasuresUseCase,
    ) -> bool:
        count = await asyncio.to_thread(use_case.execute)
        return count > 0
