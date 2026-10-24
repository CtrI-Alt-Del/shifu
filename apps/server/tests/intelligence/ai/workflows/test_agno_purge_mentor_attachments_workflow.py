"""The purge workflow run in process over the disposable PostgreSQL: a real
purge use case and repositories, with the private object store stubbed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient
import pytest

from shifu.intelligence.ai.agno.workflows import AgnoPurgeMentorAttachmentsWorkflow
from shifu.intelligence.core.domain.entities import (
    MentorAttachment,
    MentorAttachmentBatch,
)
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import MentorAttachmentInvalidError
from shifu.intelligence.core.use_cases import PurgeMentorAttachmentsUseCase
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from shifu.shared.core.domain.structures import AuthenticatedUser
from tests.fixtures.intelligence_fixture import (
    IntelligenceFixture,
    MentorAttachmentStorageStub,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

IDS = SystemIdentifierProvider()
# The workflow input requires ULID account ids; the fixture's constants are not ULIDs.
ACCOUNT = AuthenticatedUser(
    account_id=IDS.generate(), display_name='Learner', time_zone=None
)
OTHER = AuthenticatedUser(
    account_id=IDS.generate(), display_name='Other', time_zone=None
)


class Harness:
    def __init__(self, fixture: IntelligenceFixture) -> None:
        self.fixture = fixture
        self.storage = MentorAttachmentStorageStub()
        self.workflow = AgnoPurgeMentorAttachmentsWorkflow(
            PurgeMentorAttachmentsUseCase(
                fixture.database, SystemClockProvider(), self.storage
            )
        )

    def seed_batch(
        self,
        *,
        account_id: str = ACCOUNT.account_id,
        session_id: str | None = None,
        revoked: bool,
        attachments: int = 2,
    ) -> tuple[str, int, list[str]]:
        """A batch with uploaded attachments; returns its id, generation and keys."""
        now = datetime.now(UTC)
        batch = MentorAttachmentBatch.create(
            IDS.generate(), account_id, session_id, now, now + timedelta(hours=1)
        )
        if revoked:
            batch.revoke(now)
        keys: list[str] = []
        with self.fixture.database.transaction() as repositories:
            repositories.mentor_attachment_batches.add(batch)
            for index in range(attachments):
                content = f'private attachment {index}'.encode()
                object_key = f'mentor/{batch.id}/{index}.txt'
                self.storage.put(object_key, content, 'text/plain')
                keys.append(object_key)
                repositories.mentor_attachments.add(
                    MentorAttachment.create(
                        IDS.generate(),
                        account_id,
                        batch.id,
                        f'upload-{batch.id}-{index}',
                        f'notes-{index}.txt',
                        'text/plain',
                        len(content),
                        hashlib.sha256(content).hexdigest(),
                        object_key,
                        now,
                    )
                )
        return batch.id, batch.generation, keys

    def run(self, **request: object) -> int:
        output = self.workflow.run(input=json.dumps(request)).content
        assert isinstance(output, str)
        return int(json.loads(output)['removed_objects'])

    def statuses(self, batch_id: str) -> set[MentorAttachmentStatus]:
        with self.fixture.database.transaction() as repositories:
            attachments = repositories.mentor_attachments.find_by_batch_id(batch_id)
        return {attachment.status for attachment in attachments}

    def session_id(self) -> str:
        with TestClient(
            self.fixture.mentor_app(ACCOUNT),
            headers={'Authorization': 'Bearer test-token'},
        ) as client:
            return self.fixture.create_session(client)[0]


@pytest.fixture
def harness(intelligence_fixture: IntelligenceFixture) -> Iterator[Harness]:
    yield Harness(intelligence_fixture)


class TestAgnoPurgeMentorAttachmentsWorkflow:
    def test_purges_a_revoked_batch_by_id(self, harness: Harness) -> None:
        batch_id, generation, keys = harness.seed_batch(revoked=True)

        removed = harness.run(
            account_id=ACCOUNT.account_id,
            batch_id=batch_id,
            deletion_generation=generation,
        )

        assert removed == 2
        assert not any(key in harness.storage.objects for key in keys)
        assert harness.statuses(batch_id) == {MentorAttachmentStatus.REMOVED}

    def test_purges_the_revoked_batches_of_a_session(self, harness: Harness) -> None:
        session_id = harness.session_id()
        batch_id, generation, keys = harness.seed_batch(
            session_id=session_id, revoked=True
        )

        removed = harness.run(
            account_id=ACCOUNT.account_id,
            session_id=session_id,
            deletion_generation=generation,
        )

        assert removed == 2
        assert not any(key in harness.storage.objects for key in keys)
        assert harness.statuses(batch_id) == {MentorAttachmentStatus.REMOVED}

    def test_ignores_a_stale_deletion_generation(self, harness: Harness) -> None:
        batch_id, generation, keys = harness.seed_batch(revoked=True)

        removed = harness.run(
            account_id=ACCOUNT.account_id,
            batch_id=batch_id,
            deletion_generation=generation - 1,
        )

        assert removed == 0
        assert all(key in harness.storage.objects for key in keys)
        assert harness.statuses(batch_id) == {MentorAttachmentStatus.UPLOADING}

    def test_ignores_another_accounts_batch(self, harness: Harness) -> None:
        batch_id, generation, keys = harness.seed_batch(
            account_id=OTHER.account_id, revoked=True
        )

        removed = harness.run(
            account_id=ACCOUNT.account_id,
            batch_id=batch_id,
            deletion_generation=generation,
        )

        assert removed == 0
        assert all(key in harness.storage.objects for key in keys)

    def test_is_idempotent(self, harness: Harness) -> None:
        batch_id, generation, _ = harness.seed_batch(revoked=True)
        request = {
            'account_id': ACCOUNT.account_id,
            'batch_id': batch_id,
            'deletion_generation': generation,
        }

        assert harness.run(**request) == 2
        assert harness.run(**request) == 2  # the keys are removed again, safely
        assert harness.statuses(batch_id) == {MentorAttachmentStatus.REMOVED}

    @pytest.mark.parametrize(
        'request_body',
        [
            {'account_id': ACCOUNT.account_id, 'deletion_generation': 1},
            {
                'account_id': ACCOUNT.account_id,
                'batch_id': '0' * 26,
                'session_id': '0' * 26,
                'deletion_generation': 1,
            },
            {
                'account_id': ACCOUNT.account_id,
                'batch_id': 'not-a-ulid',
                'deletion_generation': 1,
            },
        ],
    )
    def test_rejects_a_request_without_exactly_one_valid_target(
        self, harness: Harness, request_body: dict[str, object]
    ) -> None:
        with pytest.raises(MentorAttachmentInvalidError):
            harness.workflow.run(input=json.dumps(request_body))
