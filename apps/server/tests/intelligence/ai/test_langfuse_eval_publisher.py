"""The opt-in Langfuse publisher mirrors an eval as a dataset and a scored run.

It sends the synthetic case content to Langfuse, while the JSON report keeps
leaving that content out. A missing key stops the command before any case runs.
"""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, create_autospec

from agno.agent import Agent
from agno.eval.suite import Case
from agno.scorer.base import Score, Scorer
from langfuse import Langfuse

from evals.eval import Eval
from evals.langfuse_eval_publisher import LangfuseEvalPublisher
from evals.run import main

if TYPE_CHECKING:
    from pathlib import Path

CASE_INPUT = 'Pergunta sintética sobre listas em Python'
ANSWER = {'answer': 'Use len(lista) para saber o tamanho.'}


class _FixedScorer(Scorer):
    def __init__(self, *, passed: bool) -> None:
        self.passed = passed

    async def ascore(self, run: Any, expected: Any = None) -> Score:
        del run, expected
        reason = 'accepted' if self.passed else 'rejected'
        return Score(value=int(self.passed), passed=self.passed, reason=reason)


class _TwoCaseEval(Eval):
    selector = 'two-cases'
    workflow_id = 'two-cases'
    prompt_revision = 'prompt-r1'

    def __init__(self) -> None:
        super().__init__(mode='double')
        model = Eval.SyntheticModel(lambda _text, _format: ANSWER, profile='test')
        self.agent = Agent(name='two-case-agent', model=model, retries=0)

    def cases(self) -> tuple[Case, ...]:
        return (
            Case(
                name='accepted',
                agent=self.agent,
                input=CASE_INPUT,
                expected={'mentions': 'len'},
                tags=('smoke',),
                scorer=_FixedScorer(passed=True),
            ),
            Case(
                name='rejected',
                agent=self.agent,
                input='Outra pergunta',
                scorer=_FixedScorer(passed=False),
            ),
        )


def _client() -> MagicMock:
    client = create_autospec(Langfuse, instance=True)
    items: list[MagicMock] = []

    def create_item(**kwargs: Any) -> None:
        item = MagicMock()
        item.id = kwargs['id']
        item.metadata = kwargs['metadata']
        items.append(item)

    client.create_dataset_item.side_effect = create_item
    client.get_dataset.return_value.items = items
    return client


def test_should_publish_cases_answers_and_scores_as_an_experiment_run() -> None:
    client = _client()
    evaluator = _TwoCaseEval()
    report = evaluator.run(evaluator.cases())
    publisher = LangfuseEvalPublisher(
        client, started_at=datetime(2026, 11, 23, 13, 0, tzinfo=UTC)
    )

    publisher.publish(evaluator, report)

    assert client.create_dataset.call_args.kwargs['name'] == 'shifu-evals/two-cases'
    first_item = client.create_dataset_item.call_args_list[0].kwargs
    assert first_item['id'] == 'two-cases:accepted'
    assert first_item['input'] == CASE_INPUT
    assert first_item['expected_output'] == {'mentions': 'len'}
    assert first_item['metadata']['tags'] == ['smoke']
    experiment = client.run_experiment.call_args.kwargs
    assert experiment['name'] == 'shifu-evals/two-cases'
    assert experiment['run_name'] == 'prompt-r1 · double · 2026-11-23T13:00:00Z'
    assert [item.id for item in experiment['data']] == [
        'two-cases:accepted',
        'two-cases:rejected',
    ]
    accepted, rejected = experiment['data']
    assert json.loads(experiment['task'](item=accepted)) == ANSWER
    verdict = experiment['evaluators'][0]
    passed = verdict(metadata=accepted.metadata)
    failed = verdict(metadata=rejected.metadata)
    assert (passed.name, passed.value, passed.comment) == ('passed', 1.0, 'accepted')
    assert (failed.value, failed.comment) == (0.0, 'rejected')
    client.flush.assert_called_once()


def test_should_leave_cases_outside_the_selection_out_of_the_run() -> None:
    client = _client()
    evaluator = _TwoCaseEval()
    report = evaluator.run(evaluator.select(name='accepted', tag=None))
    stale = MagicMock()
    stale.id = 'two-cases:rejected'
    client.get_dataset.return_value.items.append(stale)

    LangfuseEvalPublisher(client).publish(evaluator, report)

    experiment = client.run_experiment.call_args.kwargs
    assert [item.id for item in experiment['data']] == ['two-cases:accepted']


def test_should_keep_case_content_out_of_the_report() -> None:
    evaluator = _TwoCaseEval()

    report = evaluator.run(evaluator.cases())

    assert CASE_INPUT not in json.dumps(report)
    assert evaluator.case_contents['accepted'].input == CASE_INPUT


def test_should_refuse_to_run_without_langfuse_keys(tmp_path: Path) -> None:
    err = io.StringIO()

    code = main(
        ['--langfuse', '--output-dir', str(tmp_path)],
        stdout=io.StringIO(),
        stderr=err,
        environ={},
    )

    assert code == 2
    assert err.getvalue().strip() == 'langfuse_unavailable'
    assert not any(tmp_path.iterdir())
