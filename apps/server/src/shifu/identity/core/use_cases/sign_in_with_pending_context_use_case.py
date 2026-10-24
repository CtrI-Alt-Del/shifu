from dataclasses import replace

from shifu.identity.core.domain.enums import AccountAccess
from shifu.identity.core.domain.structures import AuthCredentials, Authentication
from shifu.identity.core.use_cases.issue_pending_confirmation_context_use_case import (
    IssuePendingConfirmationContextUseCase,
)
from shifu.identity.core.use_cases.sign_in_use_case import SignInUseCase


class SignInWithPendingContextUseCase:
    def __init__(
        self,
        sign_in_use_case: SignInUseCase,
        issue_pending_confirmation_context_use_case: (
            IssuePendingConfirmationContextUseCase
        ),
    ) -> None:
        self._sign_in_use_case = sign_in_use_case
        self._issue_pending_confirmation_context_use_case = (
            issue_pending_confirmation_context_use_case
        )

    def execute(self, credentials: AuthCredentials) -> Authentication:
        authentication = self._sign_in_use_case.execute(credentials)
        if authentication.access is not AccountAccess.ACTIVATION_ONLY:
            return authentication

        pending_handle = self._issue_pending_confirmation_context_use_case.execute(
            authentication.profile.account_id
        )
        return replace(authentication, pending_handle=pending_handle)
