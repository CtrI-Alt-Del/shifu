"""Actual pinned-model artifact integrity through the CLI and registered job."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

from huggingface_hub.constants import HF_HUB_CACHE
from safetensors.torch import (
    load_file,  # pyright: ignore[reportUnknownVariableType] - Native stub leaves PathLike generic unspecified.
    save_file,  # pyright: ignore[reportUnknownVariableType] - Native stub leaves PathLike generic unspecified.
)
from sqlalchemy import select
import pytest

from shifu.intelligence.database.sqlalchemy.models import (
    MentorMessageModel,
    MentorResponseAttemptModel,
)
from tests.messaging.inngest.jobs.intelligence.test_answer_mentor_message_job import (
    _ControlledInference,  # pyright: ignore[reportPrivateUsage] - Reuse the real registered inference harness.
    _index_snapshot,  # pyright: ignore[reportPrivateUsage] - Compare the actual persisted active corpus.
    _publish_and_wait,  # pyright: ignore[reportPrivateUsage] - Exercise the canonical registered event.
    _seed_request,  # pyright: ignore[reportPrivateUsage] - Preserve the owning real-job setup.
    controlled_mentor_endpoint as controlled_mentor_endpoint,
    inngest_app_target as inngest_app_target,
    prepared_mentor_index as prepared_mentor_index,
)

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture


_MODEL_DIRECTORY = 'models--intfloat--multilingual-e5-small'
_REVISION = '614241f622f53c4eeff9890bdc4f31cfecc418b3'


def _digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _corrupt_isolated_artifact(snapshot: Path, fault: str) -> None:
    if fault == 'dimension':
        path = snapshot / '1_Pooling' / 'config.json'
        configuration = json.loads(path.read_text())
        configuration['word_embedding_dimension'] = 383
        path.write_text(json.dumps(configuration))
        return
    weights_path = snapshot / 'model.safetensors'
    with weights_path.open('rb') as archive:
        header_size = int.from_bytes(archive.read(8), 'little')
        header = json.loads(archive.read(header_size))
    metadata: dict[str, str] = dict(header.get('__metadata__', {}))
    weights = load_file(weights_path)
    if fault == 'nonfinite':
        key = next(name for name in weights if name.endswith('LayerNorm.weight'))
        weights[key].fill_(float('nan'))
    else:
        assert fault == 'zero_norm'
        for tensor in weights.values():
            tensor.zero_()
    corrupted_weights = weights_path.with_suffix('.corrupt.safetensors')
    save_file(weights, corrupted_weights, metadata=metadata)
    corrupted_weights.replace(weights_path)


def _run_isolated_cli(
    fixture: 'InngestFixture', cache: Path
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment.update(
        DATABASE_URL=fixture.database_url,
        HF_HOME=str(cache.parent),
        SENTENCE_TRANSFORMERS_HOME=str(cache),
        TRANSFORMERS_CACHE=str(cache),
        HF_HUB_CACHE=str(cache),
        HUGGINGFACE_HUB_CACHE=str(cache),
        HF_HUB_OFFLINE='1',
        TRANSFORMERS_OFFLINE='1',
    )
    command = [sys.executable]
    command.extend(['-m', 'shifu.mentor_indexes'])
    return subprocess.run(  # noqa: S603 - Fixed actual application CLI, isolated DB/cache only.
        command,
        cwd=Path(__file__).resolve().parents[5],
        env=environment,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


@pytest.mark.usefixtures('prepared_mentor_index')
@pytest.mark.parametrize('fault', ['dimension', 'nonfinite', 'zero_norm'])
def test_corrupt_pinned_model_copy_cannot_replace_active_index_or_break_registered_faq(
    inngest_fixture: 'InngestFixture',
    controlled_mentor_endpoint: tuple[_ControlledInference, str],
    tmp_path: Path,
    fault: str,
) -> None:
    state, _ = controlled_mentor_endpoint
    state.reset('approve')
    original = Path(HF_HUB_CACHE) / _MODEL_DIRECTORY / 'snapshots' / _REVISION
    assert original.is_dir(), 'Approved pinned model must already be installed'
    weights_hash = _digest(original / 'model.safetensors')
    pooling_hash = _digest(original / '1_Pooling' / 'config.json')
    cache = tmp_path / 'isolated-hub'
    copied = cache / _MODEL_DIRECTORY / 'snapshots' / _REVISION
    shutil.copytree(original, copied, symlinks=False)
    _corrupt_isolated_artifact(copied, fault)
    before = _index_snapshot(inngest_fixture)
    completed = _run_isolated_cli(inngest_fixture, cache)
    assert completed.returncode != 0, 'Corrupted model unexpectedly activated an index'
    expected = 'A seleção local de respostas do Mentor está indisponível.'
    diagnostic_present = expected in completed.stderr
    assert diagnostic_present, (
        'Actual corruption did not reach the expected integrity boundary: '
        f'stdout={completed.stdout!r}; stderr={completed.stderr!r}'
    )
    assert 'Mentor index activated:' not in completed.stdout
    assert _index_snapshot(inngest_fixture) == before
    assert _digest(original / 'model.safetensors') == weights_hash
    assert _digest(original / '1_Pooling' / 'config.json') == pooling_hash
    _, learner_id, attempt_id = _seed_request(
        inngest_fixture, 'O que é uma lista em Python?'
    )
    _publish_and_wait(inngest_fixture, attempt_id, 'completed')
    assert state.requests == []
    with inngest_fixture.inspection_session() as session:
        attempt = session.get(MentorResponseAttemptModel, attempt_id)
        assert attempt is not None and attempt.status == 'completed'
        assert attempt.generation_keys == [] and attempt.usage_calls == []
        response = session.scalar(
            select(MentorMessageModel).where(
                MentorMessageModel.in_reply_to_message_id == learner_id
            )
        )
        assert response is not None and response.content.strip()
    assert all(row['used_tokens'] == 0 for row in state.accounting_requests)
    assert set(state.effective_usage.values()) == {0}
