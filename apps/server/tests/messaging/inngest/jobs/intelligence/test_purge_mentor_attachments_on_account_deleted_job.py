# pyright: reportPrivateUsage=false
from datetime import UTC, datetime, timedelta
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import Mock

import pytest
from agno.workflow.types import StepInput
from agno.workflow.workflow import Workflow
from sqlalchemy import create_engine

from shifu.identity.core.domain.events import AccountDeletedEvent, AccountDeletedPayload
from shifu.intelligence.ai.agno.workflows.agno_purge_mentor_attachments_workflow import (
    AgnoPurgeMentorAttachmentsWorkflow,
)
from shifu.intelligence.core.domain.errors import MentorAttachmentInvalidError
from shifu.intelligence.core.domain.entities import MentorAttachmentBatch
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.database.sqlalchemy.models import MentorAttachmentBatchModel
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture

_DELETED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class TestPurgeMentorAttachmentsOnAccountDeletedJob:
    def test_should_register_identity_account_deleted_event_and_purge_after_retention(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        batch_id = ids.generate()
        other_account_id = ids.generate()
        other_batch_id = ids.generate()
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            database = SqlalchemyIntelligenceDatabase(engine, id_provider=ids)
            with database.transaction() as repositories:
                repositories.mentor_attachment_batches.add(
                    MentorAttachmentBatch.create(
                        batch_id,
                        account_id,
                        None,
                        _DELETED_AT,
                        _DELETED_AT + timedelta(hours=1),
                    )
                )
                repositories.mentor_attachment_batches.add(
                    MentorAttachmentBatch.create(
                        other_batch_id,
                        other_account_id,
                        None,
                        _DELETED_AT,
                        _DELETED_AT + timedelta(hours=1),
                    )
                )
        finally:
            engine.dispose()

        event = AccountDeletedEvent(
            payload=AccountDeletedPayload(
                account_id=account_id,
                deleted_at=_DELETED_AT.isoformat().replace('+00:00', 'Z'),
            )
        )
        event_id = ids.generate()
        inngest_fixture.publish(
            event.name,
            {
                'account_id': event.payload.account_id,
                'deleted_at': event.payload.deleted_at,
            },
            event_id=event_id,
        )

        inngest_fixture.wait_for_database(
            lambda session: (
                session.get(MentorAttachmentBatchModel, batch_id) is None
                and session.get(MentorAttachmentBatchModel, other_batch_id) is not None
            )
        )

    def test_should_reject_extra_account_deleted_payload_fields_without_purging(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        batch_id = ids.generate()
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            database = SqlalchemyIntelligenceDatabase(engine, id_provider=ids)
            with database.transaction() as repositories:
                repositories.mentor_attachment_batches.add(
                    MentorAttachmentBatch.create(
                        batch_id,
                        account_id,
                        None,
                        _DELETED_AT,
                        _DELETED_AT + timedelta(hours=1),
                    )
                )
        finally:
            engine.dispose()

        event = AccountDeletedEvent(
            payload=AccountDeletedPayload(
                account_id=account_id,
                deleted_at=_DELETED_AT.isoformat().replace('+00:00', 'Z'),
            )
        )
        event_id = ids.generate()
        inngest_fixture.publish(
            event.name,
            {
                'account_id': event.payload.account_id,
                'deleted_at': event.payload.deleted_at,
                'unexpected': 'must be rejected',
            },
            event_id=event_id,
        )

        inngest_fixture.wait_for_log(f'"event":"job.failed","event_id":"{event_id}"')
        with inngest_fixture.inspection_session() as session:
            assert session.get(MentorAttachmentBatchModel, batch_id) is not None


class TestPurgeMentorAttachmentsWorkflow:
    def test_should_register_private_cleanup_step_without_retries_or_telemetry(
        self,
    ) -> None:
        workflow = AgnoPurgeMentorAttachmentsWorkflow(Mock())

        assert workflow.id == 'intelligence-purge-mentor-attachments'
        assert workflow.name == 'purge-mentor-attachments'
        assert workflow.telemetry is False
        assert workflow.store_events is False
        assert workflow.store_executor_outputs is False
        steps = cast('Any', workflow.steps)
        assert steps is not None
        assert len(steps) == 1
        assert steps[0].name == 'purge-private-artifacts'
        assert steps[0].max_retries == 0
        assert steps[0].executor.__self__ is workflow

    @pytest.mark.parametrize(
        ('target', 'expected_session_id', 'expected_batch_id'),
        [
            ('session_id', 'A' * 26, None),
            ('batch_id', None, 'B' * 26),
        ],
    )
    def test_should_purge_the_active_request_and_return_removed_count(
        self,
        target: str,
        expected_session_id: str | None,
        expected_batch_id: str | None,
    ) -> None:
        account_id = 'C' * 26
        request = {
            'account_id': account_id,
            target: expected_session_id or expected_batch_id,
            'deletion_generation': 7,
        }
        use_case = Mock()
        use_case.execute.return_value = 2
        workflow = object.__new__(AgnoPurgeMentorAttachmentsWorkflow)
        workflow._purge_use_case = use_case  # noqa: SLF001
        workflow._request = ContextVar('test-purge-request', default=None)  # noqa: SLF001
        workflow._request.set(  # noqa: SLF001
            AgnoPurgeMentorAttachmentsWorkflow._parse_input(request)  # noqa: SLF001
        )

        output = workflow._purge(  # noqa: SLF001
            StepInput(input={'ignored': 'step payload'})
        )

        assert output.content == '{"removed_objects": 2}'
        use_case.execute.assert_called_once_with(
            account_id, expected_session_id, expected_batch_id, 7
        )

    def test_should_use_step_payload_and_report_noop_when_request_context_is_missing(
        self,
    ) -> None:
        account_id = 'D' * 26
        batch_id = 'E' * 26
        use_case = Mock()
        use_case.execute.return_value = 0
        workflow = object.__new__(AgnoPurgeMentorAttachmentsWorkflow)
        workflow._purge_use_case = use_case  # noqa: SLF001
        workflow._request = ContextVar('test-purge-request', default=None)  # noqa: SLF001

        output = workflow._purge(  # noqa: SLF001
            StepInput(
                input=(
                    '{"account_id":"'
                    + account_id
                    + '","batch_id":"'
                    + batch_id
                    + '","deletion_generation":3}'
                )
            )
        )

        assert output.content == '{"removed_objects": 0}'
        use_case.execute.assert_called_once_with(account_id, None, batch_id, 3)

    def test_run_normalizes_generation_and_resets_request_context(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        workflow = AgnoPurgeMentorAttachmentsWorkflow(Mock())
        observed: list[object] = []
        sentinel = object()

        def run_base(_workflow: Workflow, *, input: object) -> object:
            observed.append(workflow._request.get())  # noqa: SLF001
            observed.append(input)
            return sentinel

        monkeypatch.setattr(Workflow, 'run', run_base)

        result = workflow.run(
            '{"account_id":"F'
            + 'F' * 25
            + '","batch_id":"G'
            + 'G' * 25
            + '","deletion_generation":"4"}'
        )

        assert result is sentinel
        assert cast('Any', observed[0]).deletion_generation == 4
        assert observed[1] == (
            '{"account_id":"'
            + 'F' * 26
            + '","session_id":null,"batch_id":"'
            + 'G' * 26
            + '","deletion_generation":4}'
        )
        assert workflow._request.get() is None  # noqa: SLF001

    def test_run_resets_request_context_when_engine_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        workflow = AgnoPurgeMentorAttachmentsWorkflow(Mock())

        def run_base(_workflow: Workflow, *, input: object) -> object:
            raise RuntimeError('private workflow failure')

        monkeypatch.setattr(Workflow, 'run', run_base)

        with pytest.raises(RuntimeError, match='private workflow failure'):
            workflow.run(
                {
                    'account_id': 'H' * 26,
                    'session_id': 'J' * 26,
                    'deletion_generation': 1,
                }
            )

        assert workflow._request.get() is None  # noqa: SLF001

    def test_should_reject_malformed_requests_and_requests_without_one_target(
        self,
    ) -> None:
        for request in (
            '{not-json',
            {
                'account_id': 'K' * 26,
                'deletion_generation': 1,
            },
            {
                'account_id': 'K' * 26,
                'session_id': None,
                'batch_id': None,
                'deletion_generation': 1,
            },
        ):
            with pytest.raises(MentorAttachmentInvalidError):
                AgnoPurgeMentorAttachmentsWorkflow._parse_input(request)  # noqa: SLF001

    def test_deep_copy_preserves_use_case_and_applies_updates(self) -> None:
        use_case = Mock()
        workflow = AgnoPurgeMentorAttachmentsWorkflow(use_case)
        workflow_any = cast('Any', workflow)
        workflow_any.db = 'original-database'

        copied = workflow.deep_copy()
        updated = workflow.deep_copy(update={'db': 'updated-database'})

        assert copied is not workflow
        assert copied.db == 'original-database'
        assert copied._purge_use_case is use_case  # noqa: SLF001
        assert updated.db == 'updated-database'

    @pytest.mark.parametrize(
        ('invalid_account_id', 'invalid_deleted_at'),
        [
            (' \t', _DELETED_AT.isoformat().replace('+00:00', 'Z')),
            ('', _DELETED_AT.isoformat().replace('+00:00', 'Z')),
            (None, '2026-01-01T00:00:00'),
            (None, 'not-a-timestamp'),
            (None, '2026-01-01T00:00:00+01:00'),
        ],
    )
    def test_should_reject_invalid_canonical_payload_fields_without_purging(
        self,
        inngest_fixture: 'InngestFixture',
        invalid_account_id: str | None,
        invalid_deleted_at: str,
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        batch_id = ids.generate()
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            database = SqlalchemyIntelligenceDatabase(engine, id_provider=ids)
            with database.transaction() as repositories:
                repositories.mentor_attachment_batches.add(
                    MentorAttachmentBatch.create(
                        batch_id,
                        account_id,
                        None,
                        _DELETED_AT,
                        _DELETED_AT + timedelta(hours=1),
                    )
                )
        finally:
            engine.dispose()

        payload = AccountDeletedPayload(
            account_id=invalid_account_id or account_id,
            deleted_at=invalid_deleted_at,
        )
        if invalid_account_id is not None:
            payload = AccountDeletedPayload(
                account_id=invalid_account_id,
                deleted_at=invalid_deleted_at,
            )
        event = AccountDeletedEvent(payload=payload)
        event_id = ids.generate()
        inngest_fixture.publish(
            event.name,
            {
                'account_id': event.payload.account_id,
                'deleted_at': event.payload.deleted_at,
            },
            event_id=event_id,
        )

        inngest_fixture.wait_for_log(f'"event":"job.failed","event_id":"{event_id}"')
        with inngest_fixture.inspection_session() as session:
            assert session.get(MentorAttachmentBatchModel, batch_id) is not None
