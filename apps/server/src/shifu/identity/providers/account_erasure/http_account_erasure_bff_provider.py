from uuid import UUID

import httpx

from shifu.identity.core.interfaces import AccountErasureBffProvider


class HttpAccountErasureBffProvider(AccountErasureBffProvider):
    def __init__(
        self,
        base_url: str,
        shared_secret: str,
        *,
        timeout_seconds: float = 10,
    ) -> None:
        self._url = f'{base_url.rstrip("/")}/api/internal/identity/account-closure'
        self._shared_secret = shared_secret
        self._timeout_seconds = timeout_seconds

    def close_technical_identity(self, account_id: str, erasure_id: UUID) -> None:
        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(
                    self._url,
                    headers={'X-Shifu-Bff-Secret': self._shared_secret},
                    json={
                        'account_id': account_id,
                        'erasure_id': str(erasure_id),
                    },
                )
                response.raise_for_status()
                result = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise RuntimeError('BFF technical identity cleanup failed') from error

        if result != {'closed': True}:
            raise RuntimeError('BFF technical identity cleanup was not confirmed')
