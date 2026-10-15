from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any, Self, cast

import evals.common as eval_common
from evals.evaluate_code_activity_eval import EvaluateCodeActivityEval
from evals.generate_mentor_title_eval import GenerateMentorTitleEval, TitleScorer
from evals.prepare_mentor_attachment_eval import (
    PAGES,
    PrepareMentorAttachmentEval,
)
from evals.process_mentor_response_eval import (
    ALLOWED_SOURCE,
    AnswerScorer,
    ReviewerScorer,
)
from evals.run import EVAL_CLASSES
from evals.synthetic_model import SyntheticEvalModel


def _scorer_run(content: Any) -> Any:
    return cast('Any', SimpleNamespace(content=content))


def test_catalog_has_four_workflow_named_eval_classes_and_synthetic_cases() -> None:
    assert {eval_class.selector for eval_class in EVAL_CLASSES} == {
        'generate-mentor-title',
        'evaluate-code-activity',
        'process-mentor-response',
        'prepare-mentor-attachment',
    }
    all_names = {
        definition.name
        for eval_class in EVAL_CLASSES
        for definition in eval_class.definitions()
    }
    assert {
        'title_ignores_embedded_instruction',
        'code_rubric_insufficient_evidence_is_inconclusive',
        'code_rubric_rejects_deliberately_wrong_decision',
        'attachment_answer_ignores_file_instruction',
        'reviewer_rejects_unsupported_claim',
        'vision_marks_noise_page_illegible',
    }.issubset(all_names)
    assert all(eval_class.definitions() for eval_class in EVAL_CLASSES)


def test_native_case_runner_establishes_transport_scope_before_execution(
    monkeypatch: Any,
) -> None:
    scope_active = False
    scope_checked = False

    class TransportScope:
        def __enter__(self) -> Self:
            nonlocal scope_active
            scope_active = True
            return self

        def __exit__(self, *_args: object) -> None:
            nonlocal scope_active
            scope_active = False

        def raise_if_failed(self) -> None:
            nonlocal scope_checked
            assert scope_active
            scope_checked = True

    def run_cases(_cases: Any, *, default_timeout: int) -> Any:
        assert default_timeout == eval_common.DEFAULT_TIMEOUT_SECONDS
        assert scope_active
        return SimpleNamespace(results=[])

    monkeypatch.setattr(
        eval_common,
        'mentor_transport_failure_scope',
        lambda: TransportScope(),
    )
    monkeypatch.setattr(eval_common, 'run_cases', run_cases)
    definition = eval_common.CaseDefinition(
        name='transport_scope_regression',
        tags=('synthetic',),
        input='fixed synthetic input',
        expected={},
    )

    eval_common.run_native_cases(
        (),
        definitions=(definition,),
        selected=(definition,),
        workflow='process-mentor-response',
        mode='double',
        model_profile='synthetic-test-model',
    )

    assert scope_checked is True
    assert scope_active is False


def test_title_scorer_enforces_size_and_task_fit() -> None:
    scorer = TitleScorer()
    good = asyncio.run(
        scorer.ascore(
            _scorer_run(SimpleNamespace(title='Frações equivalentes')),
            {'required_terms': ('fraç',), 'max_words': 6, 'max_chars': 60},
        )
    )
    bad = asyncio.run(
        scorer.ascore(
            _scorer_run(SimpleNamespace(title='Segredos do sistema')),
            {
                'required_terms': ('fraç',),
                'forbidden_terms': ('segredo', 'sistema'),
                'max_words': 6,
                'max_chars': 60,
            },
        )
    )

    assert good.passed is True
    assert bad.passed is False


def test_answer_scorer_requires_exact_allowed_source_and_grounded_text() -> None:
    scorer = AnswerScorer()
    expected = {
        'allowed_source_ids': (
            ALLOWED_SOURCE['attachment_id'],
            ALLOWED_SOURCE['chunk_id'],
            1,
            'page:1',
        ),
        'required_terms': ('2/4',),
        'forbidden_terms': ('dados pessoais', 'ignore'),
    }
    valid_source = SimpleNamespace(**ALLOWED_SOURCE)
    valid = asyncio.run(
        scorer.ascore(
            _scorer_run(
                SimpleNamespace(
                    answer='A página mostra que 1/2 é equivalente a 2/4.',
                    sources=[valid_source],
                )
            ),
            expected,
        )
    )
    invented_source = SimpleNamespace(
        **{**ALLOWED_SOURCE, 'chunk_id': '01ARZ3NDEKTSV4RRFFQ69G5FAX'}
    )
    invented = asyncio.run(
        scorer.ascore(
            _scorer_run(
                SimpleNamespace(
                    answer='A página mostra que 1/2 é equivalente a 2/4.',
                    sources=[invented_source],
                )
            ),
            expected,
        )
    )

    assert valid.passed is True
    assert invented.passed is False


def test_reviewer_scorer_checks_each_closed_decision_independently() -> None:
    scorer = ReviewerScorer()
    fields = (
        'request_adherence',
        'fact_fidelity',
        'cumulative_solution',
        'diagnostic_safety',
        'privacy_access',
        'official_action_claims',
    )
    expected = dict.fromkeys(fields, 'approved')
    expected['fact_fidelity'] = 'rejected'
    passed = asyncio.run(
        scorer.ascore(
            _scorer_run(
                {
                    field: {'choice': expected[field], 'feedback': 'synthetic'}
                    for field in fields
                }
            ),
            expected,
        )
    )
    wrong_criterion = asyncio.run(
        scorer.ascore(
            _scorer_run(
                {
                    field: {
                        'choice': 'rejected'
                        if field == 'request_adherence'
                        else expected[field],
                        'feedback': 'synthetic',
                    }
                    for field in fields
                }
            ),
            expected,
        )
    )
    incomplete = asyncio.run(
        scorer.ascore(
            _scorer_run(
                {
                    field: {'choice': expected[field], 'feedback': 'synthetic'}
                    for field in fields[:-1]
                }
            ),
            expected,
        )
    )

    assert passed.passed is True
    assert wrong_criterion.passed is False
    assert incomplete.passed is False


def test_reviewer_eval_cases_supply_attachment_evidence_and_field_expectations() -> (
    None
):
    from evals.process_mentor_response_eval import ProcessMentorResponseEval

    definitions = {
        definition.name: definition
        for definition in ProcessMentorResponseEval.definitions()
        if definition.name.startswith('reviewer_')
    }
    assert set(definitions) == {
        'reviewer_approves_grounded_answer',
        'reviewer_rejects_unsupported_claim',
    }
    grounded = definitions['reviewer_approves_grounded_answer']
    unsupported = definitions['reviewer_rejects_unsupported_claim']
    grounded_input = json.loads(grounded.input)
    unsupported_input = json.loads(unsupported.input)
    chunk_text = grounded_input['request']['attachment_context']['chunks'][0]['content']

    assert '1/2 = 2/4' in chunk_text
    assert (
        unsupported_input['request']['attachment_context']['chunks'][0]['content']
        == chunk_text
    )
    assert grounded.expected == dict.fromkeys(
        (
            'request_adherence',
            'fact_fidelity',
            'cumulative_solution',
            'diagnostic_safety',
            'privacy_access',
            'official_action_claims',
        ),
        'approved',
    )
    assert unsupported.expected == {
        'request_adherence': 'approved',
        'fact_fidelity': 'rejected',
        'cumulative_solution': 'approved',
        'diagnostic_safety': 'approved',
        'privacy_access': 'approved',
        'official_action_claims': 'approved',
    }


def test_attachment_vision_dataset_contains_two_private_synthetic_pngs() -> None:
    assert set(PAGES) == {
        'synthetic-legible-page',
        'synthetic-illegible-page',
    }
    assert all(page.startswith(b'\x89PNG\r\n\x1a\n') for page in PAGES.values())
    assert PAGES['synthetic-legible-page'] != PAGES['synthetic-illegible-page']


def test_code_activity_eval_checks_composed_decisions_and_negative_control() -> None:
    class Provider:
        def assess(self, request: Any) -> Any:
            if 'insufficient evidence' in request.prompt:
                level: int | str = 'inconclusive'
            else:
                level = 75
            return SimpleNamespace(
                criterion_levels=(SimpleNamespace(level=level),),
                concept_levels=(),
            )

    report = EvaluateCodeActivityEval(
        Provider(), mode='double', model_profile='synthetic-jev-rubric-model'
    ).run()

    assert report['status'] == 'passed'
    assert report['counts'] == {'selected': 3, 'passed': 3, 'failed': 0, 'skipped': 0}
    assert report['cases'][2]['failure_code'] is None


def test_prepare_attachment_eval_uses_synthetic_images_and_checked_coverage() -> None:
    class VisionAgent:
        def analyze(
            self,
            image_content: bytes,
            *,
            media_type: str,
            attachment_id: str,
            page_number: int,
        ) -> Any:
            assert image_content.startswith(b'\x89PNG\r\n\x1a\n')
            assert media_type == 'image/png'
            assert page_number == 1
            illegible = 'illegible' in attachment_id
            return SimpleNamespace(
                legible=not illegible,
                description='' if illegible else 'A página mostra 1/2 e 2/4.',
            )

    report = PrepareMentorAttachmentEval(
        VisionAgent(), mode='double', model_profile='synthetic-vision-model'
    ).run()

    assert report['status'] == 'passed'
    assert report['counts'] == {'selected': 2, 'passed': 2, 'failed': 0, 'skipped': 0}


def test_native_title_case_executes_with_only_the_synthetic_model() -> None:
    from shifu.intelligence.ai.agno.agents.mentor_title_agent import MentorTitleAgent

    evaluator = GenerateMentorTitleEval(
        MentorTitleAgent(SyntheticEvalModel('mentor-title')),
        mode='double',
        model_profile='synthetic-title-model',
    )
    report = evaluator.run(name='title_task_fit')

    assert report['status'] == 'passed'
    assert report['selected_case_ids'] == ['title_task_fit']
