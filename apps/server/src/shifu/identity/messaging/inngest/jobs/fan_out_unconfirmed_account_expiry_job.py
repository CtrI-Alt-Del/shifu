"""Hourly fan-out for pending accounts that reached their expiry boundary."""

import asyncio
from typing import ClassVar

from inngest import Context, Function, Inngest, TriggerCron

from shifu.identity.core.use_cases import ExpireUnconfirmedAccountsUseCase


class FanOutUnconfirmedAccountExpiryJob:
    """Claim a bounded expiry batch and persist one child event per account."""

    FUNCTION_ID: ClassVar[str] = 'identity-fan-out-unconfirmed-account-expiry'
    _CRON: ClassVar[str] = '0 * * * *'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: ExpireUnconfirmedAccountsUseCase,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=FanOutUnconfirmedAccountExpiryJob.FUNCTION_ID,
            trigger=TriggerCron(cron=FanOutUnconfirmedAccountExpiryJob._CRON),
            retries=3,
        )
        async def _(context: Context) -> None:
            await context.step.run(
                'claim_expiry_batch',
                FanOutUnconfirmedAccountExpiryJob._claim_batch,
                use_case,
            )

        return _

    @staticmethod
    async def _claim_batch(
        use_case: ExpireUnconfirmedAccountsUseCase,
    ) -> list[str]:
        """Run the synchronous transaction outside the async event loop.

        The use case persists the canonical child events in the Identity outbox.
        The shared broker then publishes each row independently, preserving the
        outbox durability boundary and avoiding a second direct publication of
        the same child event from the cron function.
        """

        account_ids = await asyncio.to_thread(use_case.execute)
        return list(account_ids)
