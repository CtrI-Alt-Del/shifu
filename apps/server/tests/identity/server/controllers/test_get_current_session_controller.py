from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from httpx import Response


def test_current_session_rejection_is_safe_and_telemetry_stays_technical(
    client: TestClient,
) -> None:
    response = cast(
        'Response',
        client.get('/identity/session'),  # pyright: ignore[reportUnknownMemberType]
    )

    assert response.status_code == 401
    body = response.json()
    assert body['detail']['code'] == 'unauthorized'
    assert 'account' not in str(body).lower()
