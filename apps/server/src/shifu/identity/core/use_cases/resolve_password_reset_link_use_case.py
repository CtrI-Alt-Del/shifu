import re
from typing import ClassVar

from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
)
from shifu.identity.core.domain.structures import PasswordResetLinkStatusResult
from shifu.identity.core.interfaces import (
    AccountActionTokensRepository,
    ActionTokenProvider,
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.shared.core.interfaces import ClockProvider


class ResolvePasswordResetLinkUseCase:
    _TOKEN_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'[A-Za-z0-9_-]{43}')

    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
        action_token_provider: ActionTokenProvider,
    ) -> None:
        self._identity_database = identity_database
        self._clock_provider = clock_provider
        self._action_token_provider = action_token_provider

    def execute(self, token: str) -> PasswordResetLinkStatusResult:
        if self._TOKEN_PATTERN.fullmatch(token) is None:
            return PasswordResetLinkStatusResult(result='invalid')

        token_hash = self._action_token_provider.hash(token)
        now = self._clock_provider.now()
        with self._identity_database.transaction() as repositories:
            action_token = self._token_repository(repositories).find_by_hash(token_hash)
            if (
                action_token is None
                or action_token.type is not AccountActionTokenType.PASSWORD_RECOVERY
                or action_token.status is AccountActionTokenStatus.INVALIDATED
            ):
                return PasswordResetLinkStatusResult(result='invalid')

            if action_token.status is AccountActionTokenStatus.USED:
                return PasswordResetLinkStatusResult(result='used')

            if (
                action_token.status is AccountActionTokenStatus.EXPIRED
                or now >= action_token.expires_at
            ):
                return PasswordResetLinkStatusResult(result='expired')

            return PasswordResetLinkStatusResult(result='valid')

    @staticmethod
    def _token_repository(
        repositories: IdentityDatabaseRepositories,
    ) -> AccountActionTokensRepository:
        return repositories.account_action_tokens
