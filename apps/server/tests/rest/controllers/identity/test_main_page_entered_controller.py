from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from httpx import Response


class TestMainPageEnteredController:
    def test_missing_bearer_token_returns_unauthorized_without_enqueue(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/main-page-entries',
                json={},
            ),
        )

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'
