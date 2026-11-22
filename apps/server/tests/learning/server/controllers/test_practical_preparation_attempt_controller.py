"""Read, submit and review a practical preparation Activity over HTTP."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import func, select

from shifu.learning.core.domain.entities import ActivityEvaluation
from shifu.learning.core.domain.enums import PracticeDraftStatus
from shifu.learning.core.domain.structures import (
    PracticalConceptEvidence,
    PracticalCriterionResult,
    PracticalPreparationResult,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.database.sqlalchemy.models import (
    ActivityAttemptModel,
    PracticeDraftModel,
    PracticePhotoModel,
)
from tests.fixtures.practice_draft_fixture import (
    AUTH_HEADERS,
    OTHER_HEADERS,
    PracticeDraftClient,
    PracticeDraftFixture,
)
from tests.fixtures.practice_photo_storage_fixture import PracticePhotoImages

if TYPE_CHECKING:
    from tests.fixtures.postgres_fixture import PostgresDatabase

RECORD_KEYS = ('cuts', 'during', 'final')
QUESTION_KEY = 'sauteed-vegetables'


def activity_path() -> str:
    return PracticeDraftFixture.draft_path().removesuffix('/practice-draft')


def upload(client: PracticeDraftClient, record_key: str) -> int:
    name, content, media_type = PracticePhotoImages.file('image/png')
    response = client.client.put(
        f'{PracticeDraftFixture.draft_path()}/photos/{record_key}',
        files={'file': (name, content, media_type)},
        data={'upload_key': str(uuid4())},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200, response.text
    return int(response.json()['revision'])


def fill_draft(client: PracticeDraftClient, reflection: str | None = None) -> int:
    """Upload the three photos; the global rate limit allows few requests per test,
    so the reflection is saved only when the test needs it."""
    revision = 0
    for record_key in RECORD_KEYS:
        revision = upload(client, record_key)
    if reflection is not None:
        response = client.client.put(
            f'{PracticeDraftFixture.draft_path()}/reflection',
            json={'reflection': reflection},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200, response.text
        revision = int(response.json()['revision'])
    return revision


_ACTIVITY_REVISION: list[str] = []


def read_revision(client: PracticeDraftClient) -> str:
    """The Activity revision is stable for the fixture Activity: read it once."""
    if not _ACTIVITY_REVISION:
        response = client.client.get(activity_path(), headers=AUTH_HEADERS)
        assert response.status_code == 200, response.text
        _ACTIVITY_REVISION.append(str(response.json()['activity_revision']))
    return _ACTIVITY_REVISION[0]


def submit(
    client: PracticeDraftClient,
    revision: int,
    *,
    submission_key: str | None = None,
    extra: dict[str, object] | None = None,
) -> tuple[int, dict[str, object], str]:
    key = submission_key or str(uuid4())
    response = client.client.post(
        f'{activity_path()}/attempts',
        json={
            'submission_key': key,
            'activity_revision': read_revision(client),
            'answers': [
                {
                    'question_key': QUESTION_KEY,
                    'kind': 'practical_preparation',
                    'draft_revision': revision,
                    **(extra or {}),
                }
            ],
        },
        headers=AUTH_HEADERS,
    )
    return response.status_code, response.json(), key


def counts(database: PostgresDatabase) -> tuple[int, int, int]:
    """Attempts, drafts and attempt-owned photos of the practical Activity."""
    with database.engine.connect() as connection:
        return (
            connection.scalar(
                select(func.count())
                .select_from(ActivityAttemptModel)
                .where(
                    ActivityAttemptModel.activity_id == PracticeDraftFixture.ACTIVITY_ID
                )
            )
            or 0,
            connection.scalar(select(func.count()).select_from(PracticeDraftModel))
            or 0,
            connection.scalar(
                select(func.count())
                .select_from(PracticePhotoModel)
                .where(PracticePhotoModel.owner_kind == 'attempt')
            )
            or 0,
        )


def attempt_path(attempt_id: str) -> str:
    return f'{activity_path()}/attempts/{attempt_id}'


def settle(
    database: PostgresDatabase,
    attempt_id: str,
    *,
    closed: bool,
) -> None:
    """Resolve the pending evaluation the way the workflow would."""
    result = PracticalPreparationResult(
        question_key=QUESTION_KEY,
        score=None if closed else Decimal(60),
        closed_without_grade=closed,
        criterion_results=(
            PracticalCriterionResult(
                criterion_key='cut-regularity',
                level=None if closed else 100,
                comment_key=None if closed else 'cut-regularity-100',
            ),
            PracticalCriterionResult(
                criterion_key='observable-technique',
                level=50,
                comment_key='observable-technique-50',
            ),
            PracticalCriterionResult(
                criterion_key='presentation',
                level=0,
                comment_key='presentation-0',
            ),
        ),
        unassessable_record_keys=('cuts',) if closed else (),
        concept_evidence=(
            PracticalConceptEvidence(
                concept_id='concept', value=None if closed else Decimal(60)
            ),
        ),
    )
    learning = SqlalchemyLearningDatabase(database.engine)
    with learning.transaction() as repositories:
        evaluation = repositories.activity_evaluations.find_by_attempt_id_for_update(
            attempt_id
        )
        assert isinstance(evaluation, ActivityEvaluation)
        now = evaluation.started_at
        if closed:
            evaluation.close_without_grade(now, (result,))
        else:
            evaluation.complete(Decimal(60), now, (result,))
        repositories.activity_evaluations.update(evaluation)


class TestGetPracticalPreparationActivityController:
    def test_should_return_the_public_rubric_without_internal_rules(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.get(activity_path(), headers=AUTH_HEADERS)

        assert response.status_code == 200, response.text
        body = response.json()
        assert body['can_submit'] is True
        (question,) = body['questions']
        assert question['kind'] == 'practical_preparation'
        assert question['key'] == QUESTION_KEY
        assert [item['key'] for item in question['records']] == list(RECORD_KEYS)
        assert set(question['records'][0]) == {'key', 'label', 'must_show'}
        assert [
            (item['key'], Decimal(item['weight'])) for item in question['criteria']
        ] == [
            ('cut-regularity', Decimal(40)),
            ('observable-technique', Decimal(40)),
            ('presentation', Decimal(20)),
        ]
        assert set(question['criteria'][0]) == {'key', 'name', 'description', 'weight'}
        assert set(question['references'][0]) == {'label', 'accessible_text'}
        flattened = response.text
        assert 'insufficiency' not in flattened
        assert 'inconclusive' not in flattened
        assert 'comment_key' not in flattened
        assert 'Refaça a foto' not in flattened

    def test_should_deny_another_account(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.get(activity_path(), headers=OTHER_HEADERS)

        assert response.status_code == 404, response.text


class TestSubmitPracticalPreparationController:
    def test_should_create_one_pending_attempt_and_close_the_draft(
        self, practice_client: PracticeDraftClient
    ) -> None:
        revision = fill_draft(practice_client)

        status, body, _key = submit(practice_client, revision)

        assert status == 201, body
        assert body['status'] == 'pending'
        assert str(body['result_url']).endswith(f'/attempts/{body["attempt_id"]}')
        assert counts(practice_client.database) == (1, 1, 3)
        with practice_client.database.engine.connect() as connection:
            assert connection.scalar(select(PracticeDraftModel.status)) == (
                PracticeDraftStatus.CONSUMED.value
            )

    def test_should_replay_the_same_submission_key_without_a_second_attempt(
        self, practice_client: PracticeDraftClient
    ) -> None:
        revision = fill_draft(practice_client)
        _status, first, key = submit(practice_client, revision)

        status, second, _ = submit(practice_client, revision, submission_key=key)

        assert status == 200, second
        assert second['attempt_id'] == first['attempt_id']
        assert counts(practice_client.database)[0] == 1

    def test_should_refuse_a_stale_draft_revision_with_the_conflict_code(
        self, practice_client: PracticeDraftClient
    ) -> None:
        revision = fill_draft(practice_client)

        status, body, _key = submit(practice_client, revision - 1)

        assert status == 409, body
        assert body['code'] == 'practice_draft_conflict'
        assert counts(practice_client.database)[0] == 0

    def test_should_refuse_a_late_edit_after_the_draft_was_saved_again(
        self, practice_client: PracticeDraftClient
    ) -> None:
        revision = fill_draft(practice_client)
        practice_client.client.put(
            f'{PracticeDraftFixture.draft_path()}/reflection',
            json={'reflection': 'Outra reflexão.'},
            headers=AUTH_HEADERS,
        )

        status, body, _key = submit(practice_client, revision)

        assert status == 409, body
        assert body['code'] == 'practice_draft_conflict'
        assert counts(practice_client.database)[0] == 0

    def test_should_refuse_when_a_record_has_no_photo(
        self, practice_client: PracticeDraftClient
    ) -> None:
        revision = upload(practice_client, 'cuts')

        status, body, _key = submit(practice_client, revision)

        assert status == 409, body
        assert body['code'] == 'practice_draft_incomplete'
        assert counts(practice_client.database) == (0, 1, 0)

    def test_should_not_block_the_submit_on_an_empty_reflection(
        self, practice_client: PracticeDraftClient
    ) -> None:
        revision = fill_draft(practice_client, reflection='')

        status, body, _key = submit(practice_client, revision)

        assert status == 201, body

    def test_should_accept_the_client_reflection_without_using_it(
        self, practice_client: PracticeDraftClient
    ) -> None:
        revision = fill_draft(practice_client, reflection='Salva no rascunho.')

        status, body, _key = submit(
            practice_client, revision, extra={'reflection': 'Texto do cliente.'}
        )

        assert status == 201, body
        result = practice_client.client.get(
            attempt_path(str(body['attempt_id'])), headers=AUTH_HEADERS
        )
        assert result.json()['questions'][0]['reflection'] == 'Salva no rascunho.'

    def test_should_refuse_a_new_photo_after_the_attempt_was_submitted(
        self, practice_client: PracticeDraftClient
    ) -> None:
        revision = fill_draft(practice_client)
        submit(practice_client, revision)
        name, content, media_type = PracticePhotoImages.file('image/png')

        response = practice_client.client.put(
            f'{PracticeDraftFixture.draft_path()}/photos/cuts',
            files={'file': (name, content, media_type)},
            data={'upload_key': str(uuid4())},
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 409, response.text
        assert counts(practice_client.database)[2] == 3

    def test_should_refuse_a_malformed_answer_shape(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.post(
            f'{activity_path()}/attempts',
            json={
                'submission_key': str(uuid4()),
                'activity_revision': read_revision(practice_client),
                'answers': [
                    {
                        'question_key': QUESTION_KEY,
                        'kind': 'practical_preparation',
                        'text': 'resposta',
                    }
                ],
            },
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 422, response.text
        assert counts(practice_client.database)[0] == 0

    def test_should_deny_another_account(
        self, practice_client: PracticeDraftClient
    ) -> None:
        revision = fill_draft(practice_client)
        response = practice_client.client.post(
            f'{activity_path()}/attempts',
            json={
                'submission_key': str(uuid4()),
                'activity_revision': read_revision(practice_client),
                'answers': [
                    {
                        'question_key': QUESTION_KEY,
                        'kind': 'practical_preparation',
                        'draft_revision': revision,
                    }
                ],
            },
            headers=OTHER_HEADERS,
        )

        assert response.status_code == 404, response.text
        assert counts(practice_client.database)[0] == 0

    def test_should_keep_new_submissions_blocked_while_the_evaluation_is_pending(
        self, practice_client: PracticeDraftClient
    ) -> None:
        revision = fill_draft(practice_client)
        submit(practice_client, revision)

        status, body, _key = submit(practice_client, revision)

        assert status == 409, body
        assert counts(practice_client.database)[0] == 1


class TestGetPracticalPreparationAttemptController:
    def _submitted(
        self,
        practice_client: PracticeDraftClient,
        reflection: str | None = 'Cortei fino.',
    ) -> str:
        revision = fill_draft(practice_client, reflection=reflection)
        _status, body, _key = submit(practice_client, revision)
        return str(body['attempt_id'])

    def test_should_show_a_pending_attempt_with_frozen_photos_and_reflection(
        self, practice_client: PracticeDraftClient
    ) -> None:
        attempt_id = self._submitted(practice_client)

        response = practice_client.client.get(
            attempt_path(attempt_id), headers=AUTH_HEADERS
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body['status'] == 'pending'
        (question,) = body['questions']
        assert question['kind'] == 'practical_preparation'
        assert question['reflection'] == 'Cortei fino.'
        assert question['closed_without_grade'] is False
        assert [item['record_key'] for item in question['photos']] == list(RECORD_KEYS)
        assert all('level' not in item for item in question['criteria'])

    def test_should_show_the_completed_result_per_criterion(
        self, practice_client: PracticeDraftClient
    ) -> None:
        attempt_id = self._submitted(practice_client)
        settle(practice_client.database, attempt_id, closed=False)

        response = practice_client.client.get(
            attempt_path(attempt_id), headers=AUTH_HEADERS
        )

        body = response.json()
        assert response.status_code == 200, response.text
        assert body['status'] == 'completed'
        assert Decimal(body['score']) == Decimal(60)
        (question,) = body['questions']
        assert question['closed_without_grade'] is False
        assert Decimal(question['score']) == Decimal(60)
        assert [
            (item['key'], Decimal(item['weight']), item['level'], item['comment'])
            for item in question['criteria']
        ] == [
            (
                'cut-regularity',
                Decimal(40),
                100,
                'Regularidade dos cortes: nível 100 observável nas fotos.',
            ),
            (
                'observable-technique',
                Decimal(40),
                50,
                'Técnica observável: nível 50 observável nas fotos.',
            ),
            (
                'presentation',
                Decimal(20),
                0,
                'Apresentação: nível 0 observável nas fotos.',
            ),
        ]
        assert question['unassessable_records'] == []
        assert 'guidance' not in question

    def test_should_show_a_closed_attempt_as_no_grade_never_as_zero(
        self, practice_client: PracticeDraftClient
    ) -> None:
        attempt_id = self._submitted(practice_client)
        settle(practice_client.database, attempt_id, closed=True)

        response = practice_client.client.get(
            attempt_path(attempt_id), headers=AUTH_HEADERS
        )

        body = response.json()
        assert response.status_code == 200, response.text
        assert body['status'] == 'closed_without_grade'
        assert 'score' not in body
        assert body['retry_allowed'] is False
        (question,) = body['questions']
        assert question['closed_without_grade'] is True
        assert 'score' not in question
        assert question['unassessable_records'] == [
            {
                'key': 'cuts',
                'label': 'Cortes',
                'comment': 'Refaça a foto dos cortes com os legumes bem visíveis.',
            }
        ]
        assert (
            question['guidance']
            == 'Refaça a foto dos cortes com os legumes bem visíveis.'
        )
        assert question['criteria'][0] == {
            'key': 'cut-regularity',
            'name': 'Regularidade dos cortes',
            'weight': question['criteria'][0]['weight'],
        }
        assert question['reflection'] == 'Cortei fino.'
        assert len(question['photos']) == 3

    def test_should_let_the_learner_submit_again_after_a_closed_attempt(
        self, practice_client: PracticeDraftClient
    ) -> None:
        attempt_id = self._submitted(practice_client, reflection=None)
        settle(practice_client.database, attempt_id, closed=True)
        revision = fill_draft(practice_client)

        status, body, _key = submit(practice_client, revision)

        assert status == 201, body
        assert body['attempt_id'] != attempt_id
        assert counts(practice_client.database)[0] == 2

    def test_should_keep_the_closed_result_after_returning_to_it(
        self, practice_client: PracticeDraftClient
    ) -> None:
        attempt_id = self._submitted(practice_client)
        settle(practice_client.database, attempt_id, closed=True)

        first = practice_client.client.get(
            attempt_path(attempt_id), headers=AUTH_HEADERS
        ).json()
        second = practice_client.client.get(
            attempt_path(attempt_id), headers=AUTH_HEADERS
        ).json()

        assert first == second
        assert first['status'] == 'closed_without_grade'

    def test_should_deny_another_account(
        self, practice_client: PracticeDraftClient
    ) -> None:
        attempt_id = self._submitted(practice_client)

        response = practice_client.client.get(
            attempt_path(attempt_id), headers=OTHER_HEADERS
        )

        assert response.status_code == 404, response.text


class TestGetPracticeAttemptPhotoController:
    def _photo_path(self, practice_client: PracticeDraftClient) -> tuple[str, str]:
        revision = fill_draft(practice_client)
        _status, body, _key = submit(practice_client, revision)
        attempt_id = str(body['attempt_id'])
        detail = practice_client.client.get(
            attempt_path(attempt_id), headers=AUTH_HEADERS
        ).json()
        photo_id = detail['questions'][0]['photos'][0]['photo_id']
        return (
            attempt_id,
            f'{attempt_path(attempt_id)}/practice-photos/{photo_id}/content',
        )

    def test_should_serve_the_attempt_photo_privately_to_its_owner(
        self, practice_client: PracticeDraftClient
    ) -> None:
        _attempt_id, path = self._photo_path(practice_client)

        response = practice_client.client.get(path, headers=AUTH_HEADERS)

        assert response.status_code == 200, response.text
        assert response.headers['content-type'] == 'image/png'
        assert response.headers['cache-control'] == 'private, no-store'
        assert response.headers['x-content-type-options'] == 'nosniff'
        assert response.content.startswith(b'\x89PNG')

    def test_should_deny_another_account_without_revealing_the_photo(
        self, practice_client: PracticeDraftClient
    ) -> None:
        _attempt_id, path = self._photo_path(practice_client)

        response = practice_client.client.get(path, headers=OTHER_HEADERS)

        assert response.status_code == 404, response.text
        assert not response.content.startswith(b'\x89PNG')

    def test_should_require_authentication(
        self, practice_client: PracticeDraftClient
    ) -> None:
        _attempt_id, path = self._photo_path(practice_client)

        response = practice_client.client.get(path)

        assert response.status_code == 401, response.text

    def test_should_not_find_an_unknown_photo(
        self, practice_client: PracticeDraftClient
    ) -> None:
        attempt_id, _path = self._photo_path(practice_client)

        response = practice_client.client.get(
            f'{attempt_path(attempt_id)}/practice-photos/01SHF000000000000000009998/content',
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 404, response.text

    def test_should_reject_a_malformed_photo_identifier(
        self, practice_client: PracticeDraftClient
    ) -> None:
        attempt_id, _path = self._photo_path(practice_client)

        response = practice_client.client.get(
            f'{attempt_path(attempt_id)}/practice-photos/not-an-id/content',
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 422, response.text
