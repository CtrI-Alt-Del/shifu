from datetime import UTC, datetime
from typing import ClassVar

from faker import Faker

from shifu.communication.core.domain.entities import PushSubscription
from shifu.fakers.shared.id_provider_faker import IdProviderFaker


class PushSubscriptionFaker:
    _faker: ClassVar[Faker] = Faker('pt_BR')
    _id_provider: ClassVar[IdProviderFaker] = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        endpoint: str | None = None,
        p256dh_key: str | None = None,
        auth_secret: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> PushSubscription:
        created = created_at or datetime.now(UTC)
        return PushSubscription(
            id=id if id is not None else cls._id_provider.generate(),
            account_id=(
                account_id if account_id is not None else cls._id_provider.generate()
            ),
            endpoint=(
                endpoint
                if endpoint is not None
                else f'https://push.example.test/send/{cls._faker.uuid4()}'
            ),
            p256dh_key=(
                p256dh_key
                if p256dh_key is not None
                else cls._faker.pystr(min_chars=87, max_chars=87)
            ),
            auth_secret=(
                auth_secret
                if auth_secret is not None
                else cls._faker.pystr(min_chars=22, max_chars=22)
            ),
            created_at=created,
            updated_at=updated_at or created,
        )
