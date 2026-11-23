from tests.fixtures.practice_draft_fixture import (
    AUTH_HEADERS,
    OTHER_HEADERS,
    PracticeDraftClient,
    PracticeDraftFixture,
)
from tests.fixtures.practice_photo_storage_fixture import PracticePhotoImages
from sqlalchemy import select

from shifu.shared.database.sqlalchemy.models import EventModel

UPLOAD_KEY = '8b3a3f4e-2f1c-4c52-9d0b-1c2d3e4f5a6b'


def _photo_path(record_key: str = 'cuts') -> str:
    return f'{PracticeDraftFixture.draft_path()}/photos/{record_key}'


def _upload(practice: PracticeDraftClient) -> str:
    response = practice.client.put(
        _photo_path(),
        files={'file': PracticePhotoImages.file()},
        data={'upload_key': UPLOAD_KEY},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200, response.text
    return response.json()['photos'][0]['photo_id']


def _cleanup_events(practice: PracticeDraftClient) -> list[str]:
    with practice.database.engine.connect() as connection:
        rows = connection.execute(
            select(EventModel.payload).where(
                EventModel.name == 'learning/practice-photo.cleanup.requested'
            )
        ).all()
    return [row.payload['photo_id'] for row in rows]


class TestRemovePracticePhotoController:
    def test_should_hide_the_photo_at_once_and_request_cleanup(
        self, practice_client: PracticeDraftClient
    ) -> None:
        photo_id = _upload(practice_client)

        response = practice_client.client.delete(_photo_path(), headers=AUTH_HEADERS)

        assert response.status_code == 200, response.text
        assert response.json()['photos'] == []
        assert response.json()['revision'] == 2
        assert _cleanup_events(practice_client) == [photo_id]
        content = practice_client.client.get(
            f'{_photo_path()}/content', headers=AUTH_HEADERS
        )
        assert content.status_code == 404, content.text

    def test_should_be_idempotent_for_a_record_without_a_photo(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.delete(_photo_path(), headers=AUTH_HEADERS)

        assert response.status_code == 200, response.text
        assert response.json() == {'revision': 0, 'reflection': '', 'photos': []}
        assert _cleanup_events(practice_client) == []

    def test_should_reject_an_unknown_record(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.delete(
            _photo_path('unknown'), headers=AUTH_HEADERS
        )

        assert response.status_code == 400, response.text

    def test_should_deny_another_account_and_keep_the_photo(
        self, practice_client: PracticeDraftClient
    ) -> None:
        _upload(practice_client)

        response = practice_client.client.delete(_photo_path(), headers=OTHER_HEADERS)

        assert response.status_code == 404, response.text
        assert _cleanup_events(practice_client) == []
