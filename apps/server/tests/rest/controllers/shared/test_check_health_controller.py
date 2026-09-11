from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from httpx import Response


class TestCheckHealthController:
    def test_check_health(self, client: TestClient) -> None:
        response = cast('Response', client.get('/health'))  # pyright: ignore[reportUnknownMemberType]

        assert response.status_code == 200
        assert response.json() == {'status': 'ok', 'name': 'Shifu API'}
