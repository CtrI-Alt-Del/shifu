from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from httpx import Response


class TestGetCurrentSessionController:
    def test_missing_bearer_token_returns_safe_unauthorized(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.get('/identity/session'),  # pyright: ignore[reportUnknownMemberType]
        )

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'
