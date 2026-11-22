from typing import cast

from shifu.identity.core.domain.structures.account_external_effect_receipt import (
    AccountExternalEffectReceiptAdmission,
    AccountExternalEffectReceiptState,
)
from shifu.identity.database.sqlalchemy.models.account_external_effect_receipt_model import (
    AccountExternalEffectReceiptModel,
)


class AccountExternalEffectReceiptMapper:
    @staticmethod
    def to_admission(
        model: AccountExternalEffectReceiptModel, *, is_new: bool
    ) -> AccountExternalEffectReceiptAdmission:
        if model.state not in {'in_flight', 'settled', 'unknown'}:
            raise RuntimeError('Unknown external effect receipt state')
        return AccountExternalEffectReceiptAdmission(
            account_id=model.account_id,
            effect_id=model.effect_id,
            operation=model.operation,
            admitted_at=model.admitted_at,
            state=cast('AccountExternalEffectReceiptState', model.state),
            is_new=is_new,
        )
