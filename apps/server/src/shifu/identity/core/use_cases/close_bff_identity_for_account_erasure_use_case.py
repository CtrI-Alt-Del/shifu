from uuid import UUID

from shifu.identity.core.interfaces import AccountErasureBffProvider
from shifu.shared.core.interfaces import AccountErasureTargetProvider


class CloseBffIdentityForAccountErasureUseCase:
    """Retry the technical Better Auth cleanup for a pending account erasure."""

    def __init__(
        self,
        target_provider: AccountErasureTargetProvider,
        bff_provider: AccountErasureBffProvider,
    ) -> None:
        self._target_provider = target_provider
        self._bff_provider = bff_provider

    def execute(self, erasure_id: UUID) -> None:
        account_id = self._target_provider.resolve_account_id(erasure_id)
        if account_id is None:
            return

        self._bff_provider.close_technical_identity(account_id, erasure_id)
