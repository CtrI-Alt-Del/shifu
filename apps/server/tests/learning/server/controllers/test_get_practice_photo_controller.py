from tests.fixtures.practice_draft_fixture import (
    AUTH_HEADERS,
    OTHER_HEADERS,
    PracticeDraftClient,
    PracticeDraftFixture,
)
from tests.fixtures.practice_photo_storage_fixture import PracticePhotoImages

UPLOAD_KEY = '8b3a3f4e-2f1c-4c52-9d0b-1c2d3e4f5a6b'


def _content_path(record_key: str = 'cuts') -> str:
    return f'{PracticeDraftFixture.draft_path()}/photos/{record_key}/content'


class TestGetPracticePhotoController:
    def test_should_return_the_owner_photo_bytes_without_caching(
        self, practice_client: PracticeDraftClient
    ) -> None:
        file = PracticePhotoImages.file('image/webp')
        practice_client.client.put(
            f'{PracticeDraftFixture.draft_path()}/photos/cuts',
            files={'file': file},
            data={'upload_key': UPLOAD_KEY},
            headers=AUTH_HEADERS,
        )

        response = practice_client.client.get(_content_path(), headers=AUTH_HEADERS)

        assert response.status_code == 200, response.text
        stored = next(iter(practice_client.storage.objects.values()))
        assert response.content == stored
        assert stored != b''
        assert response.headers['content-type'] == 'image/webp'
        assert response.headers['cache-control'] == 'private, no-store'
        assert response.headers['x-content-type-options'] == 'nosniff'

    def test_should_not_reveal_the_photo_to_another_account(
        self, practice_client: PracticeDraftClient
    ) -> None:
        practice_client.client.put(
            f'{PracticeDraftFixture.draft_path()}/photos/cuts',
            files={'file': PracticePhotoImages.file()},
            data={'upload_key': UPLOAD_KEY},
            headers=AUTH_HEADERS,
        )

        response = practice_client.client.get(_content_path(), headers=OTHER_HEADERS)

        assert response.status_code == 404, response.text
        assert response.content != PracticePhotoImages.file()[1]

    def test_should_return_not_found_for_a_record_without_a_photo(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.get(_content_path(), headers=AUTH_HEADERS)

        assert response.status_code == 404, response.text

    def test_should_require_authentication(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.get(_content_path())

        assert response.status_code == 401, response.text
