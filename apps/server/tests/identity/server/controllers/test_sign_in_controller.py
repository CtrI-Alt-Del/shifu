from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from httpx import Response


class TestSignInController:
    def test_should_issue_a_server_verifiable_pending_handle_for_pending_credentials(
        self,
        client: TestClient,
    ) -> None:
        registration = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/registrations',
                json={
                    'display_name': 'Barbara Liskov',
                    'email': 'barbara@example.com',
                    'password': 'correct horse battery staple',
                },
            ),
        )

        assert registration.status_code == 202

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/sign-in',
                json={
                    'email': 'barbara@example.com',
                    'password': 'correct horse battery staple',
                },
            ),
        )

        assert response.status_code == 200
        body = response.json()

        assert body['access'] == 'activation-only'
        assert len(body['pending_handle']) == 43
        assert body['pending_handle'] != registration.json()['pending_handle']

        pending_status = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/pending-confirmations/status',
                json={'pending_handle': body['pending_handle']},
            ),
        )

        assert pending_status.status_code == 200
        assert pending_status.json()['state'] in {'cooldown', 'ready'}

    def test_should_serialize_profile_timestamps_as_iso_strings(
        self,
        client: TestClient,
    ) -> None:
        client.post(  # pyright: ignore[reportUnknownMemberType]
            '/identity/registrations',
            json={
                'display_name': 'Barbara Liskov',
                'email': 'barbara@example.com',
                'password': 'correct horse battery staple',
            },
        )

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/sign-in',
                json={
                    'email': 'barbara@example.com',
                    'password': 'correct horse battery staple',
                },
            ),
        )

        profile = response.json()['profile']

        assert profile['status'] == 'pending-confirmation'
        assert profile['display_name'] == 'Barbara Liskov'
        assert profile['created_at'].endswith('+00:00')
        assert datetime.fromisoformat(profile['created_at']).utcoffset() == timedelta(0)
        assert 'confirmed_at' not in profile
        assert 'time_zone' not in profile
