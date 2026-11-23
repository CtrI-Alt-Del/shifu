from sqlalchemy import select

from shifu.shared.database.sqlalchemy.models import EventModel
from tests.fixtures.practice_draft_fixture import (
    AUTH_HEADERS,
    OTHER_HEADERS,
    PracticeDraftClient,
    PracticeDraftFixture,
)
from tests.fixtures.practice_photo_storage_fixture import PracticePhotoImages

UPLOAD_KEYS = (
    '8b3a3f4e-2f1c-4c52-9d0b-1c2d3e4f5a6b',
    '0f4d6f6e-6a2b-4a8e-8d1e-5a9c1b2d3e4f',
)


class TestDiscardPracticeDraftController:
    def test_should_discard_the_draft_and_request_cleanup_for_every_photo(
        self, practice_client: PracticeDraftClient
    ) -> None:
        path = PracticeDraftFixture.draft_path()
        for record_key, upload_key in zip(('cuts', 'during'), UPLOAD_KEYS, strict=True):
            practice_client.client.put(
                f'{path}/photos/{record_key}',
                files={'file': PracticePhotoImages.file()},
                data={'upload_key': upload_key},
                headers=AUTH_HEADERS,
            )
        practice_client.client.put(
            f'{path}/reflection', json={'reflection': 'Texto.'}, headers=AUTH_HEADERS
        )

        response = practice_client.client.delete(path, headers=AUTH_HEADERS)

        assert response.status_code == 204, response.text
        read = practice_client.client.get(path, headers=AUTH_HEADERS).json()
        assert read == {'revision': 0, 'reflection': '', 'photos': []}
        with practice_client.database.engine.connect() as connection:
            events = connection.execute(
                select(EventModel.payload).where(
                    EventModel.name == 'learning/practice-photo.cleanup.requested'
                )
            ).all()
        assert len(events) == 2

    def test_should_start_a_fresh_draft_after_the_discard(
        self, practice_client: PracticeDraftClient
    ) -> None:
        path = PracticeDraftFixture.draft_path()
        practice_client.client.put(
            f'{path}/reflection', json={'reflection': 'Antigo.'}, headers=AUTH_HEADERS
        )
        practice_client.client.delete(path, headers=AUTH_HEADERS)

        response = practice_client.client.put(
            f'{path}/reflection', json={'reflection': 'Novo.'}, headers=AUTH_HEADERS
        )

        assert response.json() == {'revision': 1, 'reflection': 'Novo.', 'photos': []}

    def test_should_answer_204_when_there_is_no_draft(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.delete(
            PracticeDraftFixture.draft_path(), headers=AUTH_HEADERS
        )

        assert response.status_code == 204, response.text

    def test_should_deny_another_account_and_keep_the_draft(
        self, practice_client: PracticeDraftClient
    ) -> None:
        path = PracticeDraftFixture.draft_path()
        practice_client.client.put(
            f'{path}/reflection',
            json={'reflection': 'Meu texto.'},
            headers=AUTH_HEADERS,
        )

        response = practice_client.client.delete(path, headers=OTHER_HEADERS)

        assert response.status_code == 404, response.text
        assert (
            practice_client.client.get(path, headers=AUTH_HEADERS).json()['reflection']
            == 'Meu texto.'
        )
