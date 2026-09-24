from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountConfirmationDeliveryStatus,
)
from shifu.identity.database.sqlalchemy.models import AccountActionTokenModel


class AccountActionTokenMapper:
    @staticmethod
    def to_domain(model: AccountActionTokenModel) -> AccountActionToken:
        return AccountActionToken(
            id=model.id,
            account_id=model.account_id,
            type=AccountActionTokenType(model.type),
            status=AccountActionTokenStatus(model.status),
            token_hash=model.token_hash,
            issued_at=model.issued_at,
            expires_at=model.expires_at,
            updated_at=model.updated_at,
            used_at=model.used_at,
            invalidated_at=model.invalidated_at,
            communication_id=model.communication_id,
            pending_handle_hash=model.pending_handle_hash,
            delivery_status=(
                AccountConfirmationDeliveryStatus(model.delivery_status)
                if model.delivery_status is not None
                else None
            ),
        )

    @staticmethod
    def to_model(token: AccountActionToken) -> AccountActionTokenModel:
        return AccountActionTokenModel(
            id=token.id,
            account_id=token.account_id,
            type=token.type.value,
            status=token.status.value,
            token_hash=token.token_hash,
            issued_at=token.issued_at,
            expires_at=token.expires_at,
            updated_at=token.updated_at,
            used_at=token.used_at,
            invalidated_at=token.invalidated_at,
            communication_id=token.communication_id,
            pending_handle_hash=token.pending_handle_hash,
            delivery_status=(
                token.delivery_status.value
                if token.delivery_status is not None
                else None
            ),
        )
