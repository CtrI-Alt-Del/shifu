"""Publish eval cases and results to Langfuse as datasets and dataset runs.

The eval datasets are synthetic, so this publisher sends their content: the case
input, the expected value and the model answer. It is an explicit exception to the
runtime rule that keeps prompts and answers out of monitoring, and it only runs
when the eval command asks for it. Application traffic never goes through here.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar, cast

from langfuse import Evaluation

if TYPE_CHECKING:
    from collections.abc import Mapping

    from langfuse import Langfuse

    from evals.eval import Eval


class LangfuseEvalPublisher:
    """Mirror each eval as a Langfuse dataset and each execution as a dataset run.

    A dataset item keeps a stable id per case, so running again updates the item
    instead of adding a copy. Every execution becomes a new run, scored per case,
    which lets Langfuse compare prompt revisions side by side.
    """

    DATASET_PREFIX: ClassVar[str] = 'shifu-evals'
    MAX_TEXT_CHARS: ClassVar[int] = 20_000
    MAX_DEPTH: ClassVar[int] = 12

    def __init__(self, client: Langfuse, *, started_at: datetime | None = None) -> None:
        self._client: Langfuse = client
        self._started_at: datetime = started_at or datetime.now(UTC)

    def publish(self, evaluator: Eval, report: Mapping[str, Any]) -> None:
        selector = evaluator.selector
        dataset_name = f'{self.DATASET_PREFIX}/{selector}'
        self._client.create_dataset(
            name=dataset_name,
            description=f'Synthetic cases of the {selector} eval.',
            metadata={'workflow_id': evaluator.workflow_id},
        )
        for case_id, content in evaluator.case_contents.items():
            self._client.create_dataset_item(
                dataset_name=dataset_name,
                id=self.item_id(selector, case_id),
                input=self._jsonable(content.input),
                expected_output=self._jsonable(content.expected),
                metadata={
                    'case_id': case_id,
                    'tags': list(content.tags),
                    'dataset_revision': evaluator.dataset_revision,
                },
            )

        reports = {case['case_id']: case for case in report.get('cases', [])}
        wanted = {
            self.item_id(selector, case_id): case_id
            for case_id in evaluator.case_contents
            if case_id in reports
        }
        items = [
            item
            for item in self._client.get_dataset(dataset_name).items
            if item.id in wanted
        ]

        def answer(*, item: Any, **_kwargs: Any) -> Any:
            case_id = wanted[item.id]
            content = evaluator.case_contents[case_id]
            if content.output is not None:
                return self._jsonable(content.output)
            # A provider eval keeps no model answer; its metrics are the output.
            return self._jsonable(reports[case_id].get('metrics'))

        def verdict(*, metadata: Any = None, **_kwargs: Any) -> Evaluation:
            item_metadata = cast('dict[str, object]', metadata or {})
            case_id = str(item_metadata.get('case_id', ''))
            case_report = reports.get(case_id, {})
            content = evaluator.case_contents.get(case_id)
            reason = content.scorer_reason if content is not None else None
            return Evaluation(
                name='passed',
                value=1.0 if case_report.get('outcome') == 'passed' else 0.0,
                comment=reason or case_report.get('failure_code'),
                metadata={
                    'outcome': case_report.get('outcome'),
                    'failure_code': case_report.get('failure_code'),
                    'duration_seconds': case_report.get('duration_seconds'),
                },
            )

        # The answers were produced by the eval already; the experiment only records
        # them, so the Langfuse Experiments view can compare runs.
        self._client.run_experiment(
            name=dataset_name,
            run_name=self.run_name(evaluator),
            description=f'{evaluator.selector} eval in {evaluator.mode} mode.',
            data=items,
            task=answer,
            evaluators=[verdict],
            max_concurrency=1,
            metadata={
                'mode': str(report.get('mode')),
                'model_profile': str(report.get('model_profile')),
                'prompt_revision': evaluator.prompt_revision,
                'dataset_revision': evaluator.dataset_revision,
            },
        )
        self._client.flush()

    def run_name(self, evaluator: Eval) -> str:
        stamp = self._started_at.strftime('%Y-%m-%dT%H:%M:%SZ')
        return f'{evaluator.prompt_revision} · {evaluator.mode} · {stamp}'

    @staticmethod
    def item_id(selector: str, case_id: str) -> str:
        return f'{selector}:{case_id}'

    @classmethod
    def _jsonable(cls, value: Any, depth: int = 0) -> Any:
        """Turn a case value into JSON Langfuse can show, with long text cut."""
        if depth > cls.MAX_DEPTH:
            return '…'
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            extra = len(value) - cls.MAX_TEXT_CHARS
            if extra <= 0:
                return value
            return f'{value[: cls.MAX_TEXT_CHARS]}…[{extra} more characters]'
        if isinstance(value, (bytes, bytearray)):
            return f'<{len(value)} bytes>'
        dump = getattr(value, 'model_dump', None)
        if callable(dump):
            return cls._jsonable(dump(mode='json'), depth + 1)
        if is_dataclass(value) and not isinstance(value, type):
            return cls._jsonable(asdict(value), depth + 1)
        if isinstance(value, dict):
            mapping = cast('dict[object, object]', value)
            return {
                str(key): cls._jsonable(item, depth + 1)
                for key, item in mapping.items()
            }
        if isinstance(value, (list, tuple, set, frozenset)):
            items = cast('list[object]', list(value))  # pyright: ignore[reportUnknownArgumentType] - case values are untyped data.
            return [cls._jsonable(item, depth + 1) for item in items]
        return cls._jsonable(str(value), depth + 1)
