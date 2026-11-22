from contextlib import AbstractAsyncContextManager, AbstractContextManager
from typing import Protocol
from uuid import UUID

from shifu.shared.core.domain.structures import AuthenticatedUser


class AccountActivityProvider(Protocol):
    def activity(
        self,
        account_id: str,
        *,
        actor: AuthenticatedUser | None = None,
        allow_pending_confirmation: bool = False,
    ) -> AbstractContextManager[None]:
        """Admit one account-owned effect while closure is excluded."""
        ...

    def async_activity(
        self,
        account_id: str,
        *,
        actor: AuthenticatedUser | None = None,
        allow_pending_confirmation: bool = False,
    ) -> AbstractAsyncContextManager[None]:
        """Asynchronously admit one account-owned effect."""
        ...

    def external_effect(
        self,
        account_id: str,
        effect_id: UUID,
        operation: str,
        *,
        allow_pending_confirmation: bool = False,
        allow_durable_result_recovery: bool = False,
    ) -> AbstractContextManager[bool]:
        """Admit a remote effect or settle it from an already durable result."""
        ...

    def async_external_effect(
        self,
        account_id: str,
        effect_id: UUID,
        operation: str,
        *,
        allow_pending_confirmation: bool = False,
        allow_durable_result_recovery: bool = False,
    ) -> AbstractAsyncContextManager[bool]:
        """Asynchronously admit an effect or recover its durable result."""
        ...
