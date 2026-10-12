from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from shifu.intelligence.database.sqlalchemy.models import (
    MentorEmbeddingVersionModel,
    MentorMessageModel,
    MentorResponseAttemptModel,
)
from tests.fixtures.mentor_job_fixture import (
    assert_prepared_vectors,
    index_snapshot,
    publish_and_wait,
    run_preparation_cli,
    seed_request,
    controlled_mentor_endpoint as controlled_mentor_endpoint,
    inngest_app_target as inngest_app_target,
    prepared_mentor_index as prepared_mentor_index,
)

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture
    from tests.fixtures.mentor_job_fixture import (
        _ControlledInference,  # pyright: ignore[reportPrivateUsage] - Reuse the existing native job test harness.
    )


class TestMentorIndexRecoveryJob:
    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_active_index_rejects_same_version_replacement_and_keeps_registered_faq_available(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: 'tuple[_ControlledInference, str]',
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        before = index_snapshot(inngest_fixture)
        with inngest_fixture.inspection_session() as session:
            versions_before = tuple(
                session.execute(
                    select(
                        MentorEmbeddingVersionModel.version,
                        MentorEmbeddingVersionModel.active,
                    ).order_by(MentorEmbeddingVersionModel.version)
                ).all()
            )
        repeated = run_preparation_cli(inngest_fixture)
        assert repeated.returncode != 0
        assert 'Active immutable index cannot be replaced' in repeated.stderr
        assert 'Mentor index activated:' not in repeated.stdout
        assert index_snapshot(inngest_fixture) == before
        with inngest_fixture.inspection_session() as session:
            versions_after = tuple(
                session.execute(
                    select(
                        MentorEmbeddingVersionModel.version,
                        MentorEmbeddingVersionModel.active,
                    ).order_by(MentorEmbeddingVersionModel.version)
                ).all()
            )
        assert versions_after == versions_before
        assert_prepared_vectors(inngest_fixture)
        _, learner_id, attempt_id = seed_request(
            inngest_fixture, 'O que é uma lista em Python?'
        )
        publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert state.requests == []
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.status == 'completed'
            replies = session.scalars(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            ).all()
            assert len(replies) == 1 and replies[0].content

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_cli_recovers_inactive_prepared_version_before_registered_faq_execution(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: 'tuple[_ControlledInference, str]',
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        before = index_snapshot(inngest_fixture)
        with inngest_fixture.inspection_session() as session:
            version = session.get(MentorEmbeddingVersionModel, before[0])
            assert version is not None and version.active
            # The isolated fixture-owned control row models interruption before activation.
            version.active = False
            session.commit()
        with inngest_fixture.inspection_session() as session:
            assert (
                session.scalars(
                    select(MentorEmbeddingVersionModel).where(
                        MentorEmbeddingVersionModel.active.is_(True)
                    )
                ).all()
                == []
            )
        recovered = run_preparation_cli(inngest_fixture)
        assert recovered.returncode == 0, 'Inactive version recovery CLI failed.'
        assert f'Mentor index activated: {before[0]}' in recovered.stdout
        after = index_snapshot(inngest_fixture)
        assert after[0] == before[0]
        assert len(after[1]) == len(before[1])
        assert_prepared_vectors(inngest_fixture)
        with inngest_fixture.inspection_session() as session:
            versions = session.scalars(select(MentorEmbeddingVersionModel)).all()
            assert len(versions) == 1
            assert versions[0].version == before[0] and versions[0].active
        _, learner_id, attempt_id = seed_request(
            inngest_fixture, 'O que é uma lista em Python?'
        )
        publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert state.requests == []
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.status == 'completed'
            replies = session.scalars(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            ).all()
            assert len(replies) == 1 and replies[0].content
