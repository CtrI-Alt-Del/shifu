from unittest.mock import create_autospec
from uuid import UUID

from shifu.identity.core.interfaces import AccountErasureBffProvider
from shifu.identity.core.use_cases import (
    CloseBffIdentityForAccountErasureUseCase,
)
from shifu.shared.core.interfaces import AccountErasureTargetProvider

_ERASURE_ID = UUID('1aadb116-a2ac-4ce8-81f4-d9e442ebd7df')
_ACCOUNT_ID = 'account-private-id'


def test_should_close_bff_identity_for_pending_erasure() -> None:
    target_provider = create_autospec(AccountErasureTargetProvider, instance=True)
    target_provider.resolve_account_id.return_value = _ACCOUNT_ID
    bff_provider = create_autospec(AccountErasureBffProvider, instance=True)
    subject = CloseBffIdentityForAccountErasureUseCase(
        target_provider,
        bff_provider,
    )

    subject.execute(_ERASURE_ID)

    bff_provider.close_technical_identity.assert_called_once_with(
        _ACCOUNT_ID,
        _ERASURE_ID,
    )


def test_should_ignore_completed_or_unknown_erasure() -> None:
    target_provider = create_autospec(AccountErasureTargetProvider, instance=True)
    target_provider.resolve_account_id.return_value = None
    bff_provider = create_autospec(AccountErasureBffProvider, instance=True)
    subject = CloseBffIdentityForAccountErasureUseCase(
        target_provider,
        bff_provider,
    )

    subject.execute(_ERASURE_ID)

    bff_provider.close_technical_identity.assert_not_called()
