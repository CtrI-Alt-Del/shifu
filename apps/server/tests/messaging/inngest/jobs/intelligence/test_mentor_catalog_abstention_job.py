from typing import TYPE_CHECKING

import pytest
from sqlalchemy import delete, select

from shifu.curriculum.core.domain.entities import Skill
from shifu.curriculum.database.sqlalchemy.models import SkillModel
from shifu.intelligence.database.sqlalchemy.models import (
    MentorIndexedEmbeddingModel,
    MentorMessageModel,
    MentorResponseAttemptModel,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
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
        _ControlledInference,  # pyright: ignore[reportPrivateUsage] - Shared native job harness.
    )


class TestMentorCatalogAbstentionJob:
    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_missing_answer_vectors_abstain_without_model_calls_or_runtime_reindex(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: 'tuple[_ControlledInference, str]',
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        active_version, _ = index_snapshot(inngest_fixture)
        with inngest_fixture.inspection_session() as session:
            removed = session.execute(
                delete(MentorIndexedEmbeddingModel).where(
                    MentorIndexedEmbeddingModel.version == active_version,
                    MentorIndexedEmbeddingModel.corpus == 'answers',
                )
            )
            assert removed.rowcount > 0  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
            session.commit()
        damaged = index_snapshot(inngest_fixture)
        _, learner_id, attempt_id = seed_request(
            inngest_fixture, 'O que é uma lista em Python?'
        )
        publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert state.requests == []
        assert all(row['used_tokens'] == 0 for row in state.accounting_requests)
        assert index_snapshot(inngest_fixture) == damaged
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.status == 'completed'
            assert attempt.generation_keys == []
            assert all(
                receipt['used_tokens'] == 0 for receipt in attempt.usage_calls or []
            )
            reply = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id,
                )
            )
            assert reply is not None
            assert 'Ainda não encontrei uma resposta local confiável' in reply.content

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_public_punctuation_catalog_preparation_preserves_local_only_execution(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: 'tuple[_ControlledInference, str]',
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        previous_version, _ = index_snapshot(inngest_fixture)
        ids = SystemIdentifierProvider()
        skills = tuple(
            Skill.create(id=ids.generate(), name=text, description=text)
            for text in ('!!!', '???')
        )
        with inngest_fixture.inspection_session() as session:
            session.add_all(
                [
                    SkillModel(
                        id=skill.id,
                        name=skill.name,
                        description=skill.description,
                        initial_diagnostic_activity_ids=[],
                    )
                    for skill in skills
                ]
            )
            session.commit()
        prepared = run_preparation_cli(inngest_fixture)
        assert prepared.returncode == 0, 'Public catalog preparation failed.'
        current = index_snapshot(inngest_fixture)
        assert current[0] != previous_version
        assert_prepared_vectors(inngest_fixture)
        _, learner_id, attempt_id = seed_request(
            inngest_fixture,
            'Encontre uma Habilidade sobre decisões condicionais; como organizar meus estudos?',
        )
        publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert state.requests == []
        assert all(row['used_tokens'] == 0 for row in state.accounting_requests)
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.status == 'completed'
            assert attempt.generation_keys == []
            assert all(
                receipt['used_tokens'] == 0 for receipt in attempt.usage_calls or []
            )
            reply = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id,
                )
            )
            assert reply is not None and reply.content.strip()
        assert index_snapshot(inngest_fixture) == current
