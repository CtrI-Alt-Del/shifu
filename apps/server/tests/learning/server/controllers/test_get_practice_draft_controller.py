from tests.fixtures.practice_draft_fixture import (
    AUTH_HEADERS,
    OTHER_HEADERS,
    PracticeDraftClient,
    PracticeDraftFixture,
)
from tests.fixtures.practice_photo_storage_fixture import PracticePhotoImages


class TestGetPracticeDraftController:
    def test_should_return_an_empty_draft_without_creating_one(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.get(
            PracticeDraftFixture.draft_path(), headers=AUTH_HEADERS
        )

        assert response.status_code == 200, response.text
        assert response.json() == {'revision': 0, 'reflection': '', 'photos': []}
        assert response.headers['cache-control'] == 'private, no-store'
        assert PracticeDraftFixture.counts(practice_client.database) == (0, 0)

    def test_should_return_the_saved_reflection_revision_and_photo_states(
        self, practice_client: PracticeDraftClient
    ) -> None:
        path = PracticeDraftFixture.draft_path()
        practice_client.client.put(
            f'{path}/reflection',
            json={'reflection': 'Cortei fino.'},
            headers=AUTH_HEADERS,
        )
        name, content, media_type = PracticePhotoImages.file('image/png')
        practice_client.client.put(
            f'{path}/photos/cuts',
            files={'file': (name, content, media_type)},
            data={'upload_key': '8b3a3f4e-2f1c-4c52-9d0b-1c2d3e4f5a6b'},
            headers=AUTH_HEADERS,
        )

        response = practice_client.client.get(path, headers=AUTH_HEADERS)

        body = response.json()
        assert response.status_code == 200, response.text
        assert body['revision'] == 2
        assert body['reflection'] == 'Cortei fino.'
        assert [
            (item['record_key'], item['state'], item['media_type'])
            for item in body['photos']
        ] == [('cuts', 'ready', 'image/png')]
        stored = next(iter(practice_client.storage.objects.values()))
        assert body['photos'][0]['size_bytes'] == len(stored)

    def test_should_deny_another_account_without_revealing_the_draft(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.get(
            PracticeDraftFixture.draft_path(), headers=OTHER_HEADERS
        )

        assert response.status_code == 404, response.text

    def test_should_require_authentication(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.get(PracticeDraftFixture.draft_path())

        assert response.status_code == 401, response.text

    def test_should_return_not_found_for_an_activity_without_a_practical_question(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.get(
            PracticeDraftFixture.draft_path(activity_id='01SHF000000000000000000999'),
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 404, response.text

    def test_should_reject_a_malformed_identifier(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.get(
            PracticeDraftFixture.draft_path(goal_id='not-a-ulid'),
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 422, response.text
