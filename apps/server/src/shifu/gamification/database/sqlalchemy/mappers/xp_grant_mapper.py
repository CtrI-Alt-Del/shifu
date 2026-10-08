from typing import cast

from shifu.gamification.core.domain.entities import XpGrant
from shifu.gamification.core.domain.structures import XpOrigin
from shifu.gamification.database.sqlalchemy.models import XpGrantModel
from shifu.shared.database.sqlalchemy.serialization import Serialization


class XpGrantMapper:
    @staticmethod
    def to_domain(model: XpGrantModel) -> XpGrant:
        return XpGrant(
            id=model.id,
            account_id=model.account_id,
            fact_id=model.fact_id,
            amount=model.amount,
            origin=cast(
                'XpOrigin', Serialization.deserialize_value(model.origin, XpOrigin)
            ),
            occurred_at=model.occurred_at,
            granted_at=model.granted_at,
        )

    @staticmethod
    def to_model(grant: XpGrant) -> XpGrantModel:
        return XpGrantModel(
            id=grant.id,
            account_id=grant.account_id,
            fact_id=grant.fact_id,
            amount=grant.amount,
            origin=Serialization.serialize_value(grant.origin),
            occurred_at=grant.occurred_at,
            granted_at=grant.granted_at,
        )
