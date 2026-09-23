from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from httpx import Response


class TestGetPendingConfirmationStatusController:
    def test_pending_handle_reports_cooldown_after_registration(
        self,
        client: TestClient,
    ) -> None:
        registration = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/registrations',
                json={
                    'display_name': 'Grace Hopper',
                    'email': 'grace@example.com',
                    'password': 'correct horse battery staple',
                },
            ),
        )
        pending_handle = registration.json()['pending_handle']

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/pending-confirmations/status',
                json={'pending_handle': pending_handle},
            ),
        )

        assert response.status_code == 200
        body = response.json()
        assert body['state'] == 'cooldown'
        assert 1 <= body['retry_after_seconds'] <= 60

    def test_unknown_pending_handle_is_a_safe_delivery_issue(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/pending-confirmations/status',
                json={'pending_handle': 'A' * 43},
            ),
        )

        assert response.status_code == 200
        assert response.json() == {
            'state': 'delivery_issue',
            'retry_after_seconds': None,
        }
