from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import create_engine

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.identity.core.domain.events import AccountDeletedEvent, AccountDeletedPayload
from shifu.learning.core.domain.entities import PracticeDraft, PracticePhoto
from shifu.learning.core.domain.enums import PracticePhotoState
from shifu.learning.core.domain.events import (
    PracticePhotoCleanupRequestedEvent,
    PracticePhotoCleanupRequestedPayload,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.database.sqlalchemy.models import (
    PracticeDraftModel,
    PracticePhotoModel,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture
    from tests.fixtures.practice_photo_storage_fixture import PracticePhotoS3Stub

_DELETED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _object_key(photo_id: str) -> str:
    return f'practice-photos/{photo_id}/original'


def _seed_draft(
    inngest_fixture: InngestFixture,
    account_id: str,
    *,
    state: PracticePhotoState,
) -> tuple[str, str, str]:
    """Persist a goal, experience, draft and one photo; returns their ids."""

    ids = SystemIdentifierProvider()
    engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
    try:
        database = SqlalchemyLearningDatabase(engine, id_provider=ids)
        goal = GoalFaker.fake(account_id=account_id)
        experience = SkillExperienceFaker.fake(goal_id=goal.id)
        draft = PracticeDraft.create(
            id=ids.generate(),
            skill_experience_id=experience.id,
            activity_id=ids.generate(),
        )
        photo_id = ids.generate()
        photo = PracticePhoto.create(
            id=photo_id,
            draft_id=draft.id,
            record_key='cuts',
            object_key=_object_key(photo_id),
            media_type='image/jpeg',
            size_bytes=4,
            sha256='a' * 64,
            upload_key='8b3a3f4e-2f1c-4c52-9d0b-1c2d3e4f5a6b',
        )
        photo.state = state
        with database.transaction() as repositories:
            repositories.goals.add(goal)
        with database.transaction() as repositories:
            repositories.skill_experiences.add(experience)
        with database.transaction() as repositories:
            repositories.practice_drafts.add(draft)
            repositories.practice_photos.add(photo)
    finally:
        engine.dispose()
    return draft.id, photo_id, _object_key(photo_id)


def _storage(inngest_fixture: InngestFixture) -> PracticePhotoS3Stub:
    assert inngest_fixture.practice_photo_storage is not None
    return inngest_fixture.practice_photo_storage


def _publish_cleanup(
    inngest_fixture: InngestFixture, photo_id: str, object_key: str
) -> str:
    event = PracticePhotoCleanupRequestedEvent(
        payload=PracticePhotoCleanupRequestedPayload(
            photo_id=photo_id, object_key=object_key
        )
    )
    event_id = SystemIdentifierProvider().generate()
    inngest_fixture.publish(
        event.name,
        {
            'photo_id': event.payload.photo_id,
            'object_key': event.payload.object_key,
        },
        event_id=event_id,
    )
    return event_id


class TestPurgePracticePhotoJob:
    def test_should_delete_the_object_and_clear_the_mark_of_a_removed_photo(
        self, inngest_fixture: InngestFixture
    ) -> None:
        storage = _storage(inngest_fixture)
        _, photo_id, object_key = _seed_draft(
            inngest_fixture, 'A' * 26, state=PracticePhotoState.REMOVED
        )
        storage.put(object_key, b'jpeg')

        _publish_cleanup(inngest_fixture, photo_id, object_key)

        inngest_fixture.wait_for_database(
            lambda session: session.get(PracticePhotoModel, photo_id) is None
        )
        assert not storage.has(object_key)

    def test_should_delete_an_orphan_object_when_its_rows_were_removed(
        self, inngest_fixture: InngestFixture
    ) -> None:
        storage = _storage(inngest_fixture)
        photo_id = SystemIdentifierProvider().generate()
        object_key = _object_key(photo_id)
        storage.put(object_key, b'jpeg')

        event_id = _publish_cleanup(inngest_fixture, photo_id, object_key)

        inngest_fixture.wait_for_log(f'"event":"job.completed","event_id":"{event_id}"')
        assert not storage.has(object_key)

    def test_should_never_delete_the_object_of_a_live_photo(
        self, inngest_fixture: InngestFixture
    ) -> None:
        storage = _storage(inngest_fixture)
        _, photo_id, object_key = _seed_draft(
            inngest_fixture, 'B' * 26, state=PracticePhotoState.READY
        )
        storage.put(object_key, b'jpeg')

        event_id = _publish_cleanup(inngest_fixture, photo_id, object_key)

        inngest_fixture.wait_for_log(f'"event":"job.completed","event_id":"{event_id}"')
        assert storage.has(object_key)
        with inngest_fixture.inspection_session() as session:
            assert session.get(PracticePhotoModel, photo_id) is not None

    def test_should_reject_an_object_key_outside_the_policy_without_deleting(
        self, inngest_fixture: InngestFixture
    ) -> None:
        storage = _storage(inngest_fixture)
        photo_id = SystemIdentifierProvider().generate()
        storage.put('practice-photos/someone-else/original', b'jpeg')

        event_id = _publish_cleanup(
            inngest_fixture, photo_id, 'practice-photos/someone-else/original'
        )

        inngest_fixture.wait_for_log(f'"event":"job.failed","event_id":"{event_id}"')
        assert storage.has('practice-photos/someone-else/original')

    def test_should_reject_extra_payload_fields_without_deleting(
        self, inngest_fixture: InngestFixture
    ) -> None:
        storage = _storage(inngest_fixture)
        photo_id = SystemIdentifierProvider().generate()
        object_key = _object_key(photo_id)
        storage.put(object_key, b'jpeg')
        event_id = SystemIdentifierProvider().generate()

        inngest_fixture.publish(
            PracticePhotoCleanupRequestedEvent.EVENT_NAME,
            {'photo_id': photo_id, 'object_key': object_key, 'unexpected': 'no'},
            event_id=event_id,
        )

        inngest_fixture.wait_for_log(f'"event":"job.failed","event_id":"{event_id}"')
        assert storage.has(object_key)


class TestPurgePracticeDataOnAccountDeletedJob:
    def test_should_purge_the_deleted_account_drafts_photos_and_objects_only(
        self, inngest_fixture: InngestFixture
    ) -> None:
        storage = _storage(inngest_fixture)
        account_id = 'C' * 26
        draft_id, photo_id, object_key = _seed_draft(
            inngest_fixture, account_id, state=PracticePhotoState.READY
        )
        other_draft_id, other_photo_id, other_key = _seed_draft(
            inngest_fixture, 'D' * 26, state=PracticePhotoState.READY
        )
        storage.put(object_key, b'jpeg')
        storage.put(other_key, b'jpeg')
        event = AccountDeletedEvent(
            payload=AccountDeletedPayload(
                account_id=account_id,
                deleted_at=_DELETED_AT.isoformat().replace('+00:00', 'Z'),
            )
        )

        inngest_fixture.publish(
            event.name,
            {
                'account_id': event.payload.account_id,
                'deleted_at': event.payload.deleted_at,
            },
            event_id=SystemIdentifierProvider().generate(),
        )

        inngest_fixture.wait_for_database(
            lambda session: (
                session.get(PracticeDraftModel, draft_id) is None
                and session.get(PracticePhotoModel, photo_id) is None
                and session.get(PracticeDraftModel, other_draft_id) is not None
                and session.get(PracticePhotoModel, other_photo_id) is not None
            )
        )
        assert not storage.has(object_key)
        assert storage.has(other_key)

    def test_should_reject_extra_account_deleted_payload_fields_without_purging(
        self, inngest_fixture: InngestFixture
    ) -> None:
        account_id = 'E' * 26
        draft_id, _, object_key = _seed_draft(
            inngest_fixture, account_id, state=PracticePhotoState.READY
        )
        storage = _storage(inngest_fixture)
        storage.put(object_key, b'jpeg')
        event_id = SystemIdentifierProvider().generate()

        inngest_fixture.publish(
            AccountDeletedEvent.EVENT_NAME,
            {
                'account_id': account_id,
                'deleted_at': _DELETED_AT.isoformat().replace('+00:00', 'Z'),
                'unexpected': 'must be rejected',
            },
            event_id=event_id,
        )

        inngest_fixture.wait_for_log(f'"event":"job.failed","event_id":"{event_id}"')
        assert storage.has(object_key)
        with inngest_fixture.inspection_session() as session:
            assert session.get(PracticeDraftModel, draft_id) is not None
