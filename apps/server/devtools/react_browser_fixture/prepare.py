"""Seed an explicitly declared disposable database for SHIFU-88 browser review.

This helper always runs the repository seed, which clears the target database.
It therefore requires both an explicit database URL and an explicit disposable
database acknowledgement, and refuses the known local Compose/default ports.
It never prints the URL or starts/stops Docker, API, or Web processes.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote

from sqlalchemy.engine import make_url

from activity import _make_activity


SERVER_ROOT = Path(__file__).resolve().parents[2]


def _load_seed_and_fixture(database_url: str) -> None:
    from cryptography.fernet import Fernet

    os.environ['DATABASE_URL'] = database_url
    os.environ['SHIFU_SERVER_APP_MODE'] = 'local'
    if not os.environ.get('SHIFU_COMMUNICATION_ENCRYPTION_KEYS', '').strip():
        os.environ['SHIFU_COMMUNICATION_ENCRYPTION_KEYS'] = (
            Fernet.generate_key().decode()
        )

    from shifu.shared.database.seed import seed
    from shifu.shared.database.sqlalchemy.session import Session
    from shifu.curriculum.database.sqlalchemy.repositories import (
        SqlalchemyActivitiesRepository,
        SqlalchemyCurriculumSequencesRepository,
    )
    from shifu.curriculum.database.sqlalchemy.mappers import (
        CurriculumSequenceMapper,
    )
    from shifu.curriculum.database.sqlalchemy.models import CurriculumSequenceModel
    from shifu.curriculum.core.domain.structures import CurriculumSequence
    from sqlalchemy import select

    # The target database has been explicitly acknowledged as disposable by the
    # caller; the standard seed's clear operation is limited to that database.
    seed()
    activity, fixture_sequence = _make_activity()
    with Session.database_session() as session:
        SqlalchemyActivitiesRepository(session).add_many([activity])
        sequences = SqlalchemyCurriculumSequencesRepository(session)
        seeded_sequence = sequences.find_by_competency_id(
            fixture_sequence.competency_id
        )
        if seeded_sequence is None:
            raise RuntimeError('Seed did not create the expected competency sequence.')

        # The standard development seed already persists this sequence. Update
        # that row by appending only the fixture activity instead of inserting a
        # duplicate row for the same competency.
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


def _database_url() -> str:
    value = os.environ.get('SHIFU_REACT_FIXTURE_DATABASE_URL', '').strip()
    if not value:
        raise RuntimeError(
            'Set SHIFU_REACT_FIXTURE_DATABASE_URL to the disposable PostgreSQL URL.'
        )
    if os.environ.get('SHIFU_REACT_FIXTURE_DISPOSABLE') != '1':
        raise RuntimeError(
            'Set SHIFU_REACT_FIXTURE_DISPOSABLE=1 only after confirming the target '
            'database is disposable; preparation clears its tables.'
        )

    url = make_url(value)
    host = (url.host or '').casefold()
    port = url.port
    if (
        url.get_backend_name() != 'postgresql'
        or host != '127.0.0.1'
        or port != 15448
        or unquote(url.database or '') != 'shifu'
    ):
        raise RuntimeError(
            'Target must be a loopback PostgreSQL database named shifu on a '
            'non-default high port (not 5432 or the Compose port 54344).'
        )
    return value


def _migration_environment(database_url: str) -> dict[str, str]:
    environment = {
        key: os.environ[key]
        for key in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP')
        if key in os.environ
    }
    environment['DATABASE_URL'] = database_url
    return environment


def main() -> int:
    if not (SERVER_ROOT / 'pyproject.toml').is_file():
        raise RuntimeError('Run this helper from the repository checkout.')
    database_url = _database_url()
    subprocess.run(
        [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
        cwd=SERVER_ROOT,
        env=_migration_environment(database_url),
        check=True,
    )
    _load_seed_and_fixture(database_url)
    print('Banco descartável preparado com a conta local e a atividade React mista.')
    print('Atividade: Prática React: estado e contador (3 questões; 1 React).')
    print(
        'A URL do banco não foi exibida; a seed de desenvolvimento contém a senha da conta.'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
