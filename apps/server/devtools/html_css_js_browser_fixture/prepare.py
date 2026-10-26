"""Seed a protected disposable PostgreSQL database for SHIFU-86 browser review."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote

from sqlalchemy.engine import make_url

from activity import make_activity


SERVER_ROOT = Path(__file__).resolve().parents[2]


def _database_url() -> str:
    value = os.environ.get('SHIFU_HTML_FIXTURE_DATABASE_URL', '').strip()
    if not value:
        raise RuntimeError(
            'Set SHIFU_HTML_FIXTURE_DATABASE_URL to the disposable PostgreSQL URL.'
        )
    if os.environ.get('SHIFU_HTML_FIXTURE_DISPOSABLE') != '1':
        raise RuntimeError(
            'Set SHIFU_HTML_FIXTURE_DISPOSABLE=1 only after confirming the target '
            'database is disposable; preparation clears its tables.'
        )

    url = make_url(value)
    if (
        url.get_backend_name() != 'postgresql'
        or (url.host or '').casefold() != '127.0.0.1'
        or url.port != 15448
        or unquote(url.database or '') != 'shifu'
        or url.query
    ):
        raise RuntimeError(
            'Target must be loopback PostgreSQL database shifu on port 15448; '
            'query overrides and Compose/default database ports are refused.'
        )
    return value


def _prepare(database_url: str) -> None:
    from cryptography.fernet import Fernet

    os.environ['DATABASE_URL'] = database_url
    os.environ['SHIFU_SERVER_APP_MODE'] = 'local'
    if not os.environ.get('SHIFU_COMMUNICATION_ENCRYPTION_KEYS', '').strip():
        os.environ['SHIFU_COMMUNICATION_ENCRYPTION_KEYS'] = (
            Fernet.generate_key().decode()
        )

    from sqlalchemy import select

    from shifu.curriculum.core.domain.structures import CurriculumSequence
    from shifu.curriculum.database.sqlalchemy.mappers import CurriculumSequenceMapper
    from shifu.curriculum.database.sqlalchemy.models import CurriculumSequenceModel
    from shifu.curriculum.database.sqlalchemy.repositories import (
        SqlalchemyActivitiesRepository,
        SqlalchemyCurriculumSequencesRepository,
    )
    from shifu.shared.database.seed import seed
    from shifu.shared.database.sqlalchemy.session import Session

    seed()
    activity, fixture_sequence = make_activity()
    with Session.database_session() as session:
        SqlalchemyActivitiesRepository(session).add_many([activity])
        sequences = SqlalchemyCurriculumSequencesRepository(session)
        seeded_sequence = sequences.find_by_competency_id(
            fixture_sequence.competency_id
        )
        if seeded_sequence is None:
            raise RuntimeError('Seed did not create the expected competency sequence.')

        model = session.scalar(
            select(CurriculumSequenceModel).where(
                CurriculumSequenceModel.competency_id == fixture_sequence.competency_id
            )
        )
        if model is None:
            raise RuntimeError('Seeded competency sequence disappeared.')
        updated_sequence = CurriculumSequence(
            competency_id=seeded_sequence.competency_id,
            items=(*seeded_sequence.items, fixture_sequence.items[-1]),
        )
        model.items = CurriculumSequenceMapper.to_model(updated_sequence).items


def main() -> int:
    if not (SERVER_ROOT / 'pyproject.toml').is_file():
        raise RuntimeError('Run this helper from the repository checkout.')
    database_url = _database_url()
    environment = {
        key: os.environ[key]
        for key in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP')
        if key in os.environ
    }
    environment['DATABASE_URL'] = database_url
    subprocess.run(
        [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
        cwd=SERVER_ROOT,
        env=environment,
        check=True,
    )
    _prepare(database_url)
    print('Banco descartável preparado com conta local e Activity HTML mista.')
    print('Atividade: Prática HTML: lista de tarefas (3 questões; 1 HTML/CSS/JS).')
    print('A URL do banco não foi exibida; a seed contém a senha local da conta.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
