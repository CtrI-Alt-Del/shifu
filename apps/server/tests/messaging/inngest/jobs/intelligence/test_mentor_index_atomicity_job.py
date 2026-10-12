"""CLI fault seams preserve atomic activation and the last healthy native reader."""

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from sqlalchemy import delete, select

from shifu.curriculum.core.domain.entities import Skill
from shifu.curriculum.database.sqlalchemy.models import SkillModel
from shifu.intelligence.database.sqlalchemy.models import (
    MentorEmbeddingVersionModel,
    MentorIndexedEmbeddingModel,
)
from shifu.intelligence.database.sqlalchemy.repositories.mentor_embeddings_repository import (
    SqlalchemyMentorEmbeddingsRepository,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.messaging.inngest.jobs.intelligence.test_answer_mentor_message_job import (
    _index_snapshot,  # pyright: ignore[reportPrivateUsage] - Existing native reader harness.
    _publish_and_wait,  # pyright: ignore[reportPrivateUsage] - Existing native reader harness.
    _seed_request,  # pyright: ignore[reportPrivateUsage] - Existing native reader harness.
    controlled_mentor_endpoint as controlled_mentor_endpoint,
    inngest_app_target as inngest_app_target,
    prepared_mentor_index as prepared_mentor_index,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from shifu.intelligence.core.domain.structures import MentorIndexedEmbedding
    from tests.fixtures.inngest_fixture import InngestFixture
    from tests.messaging.inngest.jobs.intelligence.test_answer_mentor_message_job import (
        _ControlledInference,  # pyright: ignore[reportPrivateUsage] - Existing native reader harness.
    )


class _InterruptedPreparationRepository(SqlalchemyMentorEmbeddingsRepository):
    def __init__(self, session: 'Session') -> None:
        super().__init__(session)
        self.control_session = session

    def prepare_version(
        self, version: str, vectors: 'tuple[MentorIndexedEmbedding, ...]'
    ) -> None:
        mode = os.environ['SHIFU_MENTOR_PREPARATION_FAULT']
        print(f'prepared-candidate:{version}', flush=True)
        # The real encoder has already produced every native vector. Faults
        # affect only public metadata/state, never the encoder or SQL guards.
        if mode == 'duplicate_identity':
            super().prepare_version(version, (*vectors, vectors[0]))
            return
        super().prepare_version(version, vectors)
        if mode == 'missing_control':
            self.control_session.execute(
                delete(MentorEmbeddingVersionModel).where(
                    MentorEmbeddingVersionModel.version == version,
                )
            )
        elif mode == 'incomplete_corpus':
            self.control_session.execute(
                delete(MentorIndexedEmbeddingModel).where(
                    MentorIndexedEmbeddingModel.version == version,
                    MentorIndexedEmbeddingModel.corpus == 'answers',
                )
            )
        else:
            raise ValueError('Unknown isolated preparation fault')


def run_interrupted_preparation_cli() -> None:
    from shifu.mentor_indexes import main

    with patch(
        'shifu.intelligence.database.sqlalchemy.intelligence_database.SqlalchemyMentorEmbeddingsRepository',
        _InterruptedPreparationRepository,
    ):
        main()


def _run_fault_cli(
    fixture: 'InngestFixture', mode: str
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment['DATABASE_URL'] = fixture.database_url
    environment['SHIFU_MENTOR_PREPARATION_FAULT'] = mode
    command = [sys.executable]
    command.extend(
        [
            '-m',
            'tests.messaging.inngest.jobs.intelligence.test_mentor_index_atomicity_job',
        ]
    )
    return subprocess.run(  # noqa: S603 - Fixed CLI entry point and fixture-owned environment.
        command,
        cwd=Path(__file__).resolve().parents[5],
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


class TestMentorIndexAtomicityJob:
    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        'fault', ['missing_control', 'incomplete_corpus', 'duplicate_identity']
    )
    def test_failed_offline_candidate_preserves_active_vectors_and_registered_reader(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: 'tuple[_ControlledInference, str]',
        fault: str,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        before = _index_snapshot(inngest_fixture)
        skill = Skill.create(
            id=SystemIdentifierProvider().generate(),
            name='Habilidade pública de preparação interrompida',
            description='Conteúdo público para uma nova revisão do catálogo.',
        )
        with inngest_fixture.inspection_session() as session:
            session.add(
                SkillModel(
                    id=skill.id,
                    name=skill.name,
                    description=skill.description,
                    initial_diagnostic_activity_ids=[],
                )
            )
            session.commit()
        failed = _run_fault_cli(inngest_fixture, fault)
        assert failed.returncode != 0
        assert 'Mentor index activated:' not in failed.stdout
        assert (
            'Duplicate embedding identity'
            if fault == 'duplicate_identity'
            else 'ServiceUnavailableError'
        ) in failed.stderr
        candidate = next(
            line.removeprefix('prepared-candidate:')
            for line in failed.stdout.splitlines()
            if line.startswith('prepared-candidate:')
        )
        assert candidate != before[0]
        after = _index_snapshot(inngest_fixture)
        assert after[0] == before[0]
        assert set(before[1]).issubset(after[1])
        with inngest_fixture.inspection_session() as session:
            active = session.scalars(
                select(MentorEmbeddingVersionModel).where(
                    MentorEmbeddingVersionModel.active.is_(True),
                )
            ).all()
            assert len(active) == 1 and active[0].version == before[0]
            staging = session.get(MentorEmbeddingVersionModel, candidate)
            if fault == 'incomplete_corpus':
                assert staging is not None and not staging.active
                corpus = set(
                    session.scalars(
                        select(MentorIndexedEmbeddingModel.corpus).where(
                            MentorIndexedEmbeddingModel.version == candidate,
                        )
                    ).all()
                )
                assert 'intents' in corpus and 'answers' not in corpus
            else:
                assert staging is None
                assert after == before
            # Return the real public catalog to the prior revision, making the
            # retained active index compatible for a genuine native FAQ reader.
            session.execute(delete(SkillModel).where(SkillModel.id == skill.id))
            session.commit()
        _, _, attempt_id = _seed_request(
            inngest_fixture, 'O que é uma lista em Python?'
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert state.requests == []
        assert _index_snapshot(inngest_fixture) == after


if __name__ == '__main__':
    run_interrupted_preparation_cli()
