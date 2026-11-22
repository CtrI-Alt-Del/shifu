from concurrent.futures import ThreadPoolExecutor

from tests.fixtures.practice_draft_fixture import (
    AUTH_HEADERS,
    OTHER_HEADERS,
    PracticeDraftClient,
    PracticeDraftFixture,
)


def _reflection_path() -> str:
    return f'{PracticeDraftFixture.draft_path()}/reflection'


class TestSavePracticeReflectionController:
    def test_should_create_the_draft_and_return_the_saved_state(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.put(
            _reflection_path(),
            json={'reflection': 'Usei fogo alto.'},
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 200, response.text
        assert response.json() == {
            'revision': 1,
            'reflection': 'Usei fogo alto.',
            'photos': [],
        }
        assert PracticeDraftFixture.counts(practice_client.database) == (1, 0)

    def test_should_let_the_last_saved_write_win_and_grow_the_revision(
        self, practice_client: PracticeDraftClient
    ) -> None:
        practice_client.client.put(
            _reflection_path(),
            json={'reflection': 'Primeiro aparelho.'},
            headers=AUTH_HEADERS,
        )
        second = practice_client.client.put(
            _reflection_path(),
            json={'reflection': 'Segundo aparelho.'},
            headers=AUTH_HEADERS,
        )

        read = practice_client.client.get(
            PracticeDraftFixture.draft_path(), headers=AUTH_HEADERS
        )

        assert second.json()['revision'] == 2
        assert read.json() == second.json()
        assert read.json()['reflection'] == 'Segundo aparelho.'

    def test_should_keep_one_draft_and_a_coherent_state_for_concurrent_devices(
        self, practice_client: PracticeDraftClient
    ) -> None:
        def save(text: str) -> tuple[int, str]:
            response = practice_client.client.put(
                _reflection_path(), json={'reflection': text}, headers=AUTH_HEADERS
            )
            return response.status_code, text

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(save, ['Texto A', 'Texto B']))

        read = practice_client.client.get(
            PracticeDraftFixture.draft_path(), headers=AUTH_HEADERS
        ).json()
        assert [status for status, _ in outcomes] == [200, 200]
        assert PracticeDraftFixture.counts(practice_client.database) == (1, 0)
        assert read['revision'] == 2
        assert read['reflection'] in {'Texto A', 'Texto B'}

    def test_should_accept_an_empty_reflection(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.put(
            _reflection_path(), json={'reflection': ''}, headers=AUTH_HEADERS
        )

        assert response.status_code == 200, response.text

    def test_should_reject_a_reflection_over_the_limit_without_saving(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.put(
            _reflection_path(), json={'reflection': 'a' * 4001}, headers=AUTH_HEADERS
        )

        assert response.status_code == 422, response.text
        assert PracticeDraftFixture.counts(practice_client.database) == (0, 0)

    def test_should_deny_another_account_without_writing(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.put(
            _reflection_path(), json={'reflection': 'Intruso.'}, headers=OTHER_HEADERS
        )

        assert response.status_code == 404, response.text
        assert PracticeDraftFixture.counts(practice_client.database) == (0, 0)
