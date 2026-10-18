from __future__ import annotations

import json
from typing import Any

import httpx

from evals.evaluate_code_activity_eval import EvaluateCodeActivityEval
from evals.generate_mentor_title_eval import GenerateMentorTitleEval
from evals.prepare_mentor_attachment_eval import PrepareMentorAttachmentEval
from evals.process_mentor_response_eval import ProcessMentorResponseEval
from evals.synthetic_model import SyntheticEvalModel


def build_evaluator(selector: str, *, mode: str) -> Any:
    """Build one quality target without starting a registry, worker, or database."""
    from shifu.intelligence.ai.eval_factories import (
        build_code_rubric_eval_provider,
        build_mentor_attachment_vision_eval_agent,
        build_mentor_title_eval_agent,
        build_process_mentor_response_eval_agents,
    )
    from shifu.shared.settings import Settings

    # Eval targets have no registry or database dependency; the required URL is inert.
    settings = Settings(redis_url='redis://127.0.0.1:6379')
    double = mode == 'double'

    if selector == GenerateMentorTitleEval.selector:
        model = SyntheticEvalModel('mentor-title') if double else None
        agent = build_mentor_title_eval_agent(settings, model=model)
        return GenerateMentorTitleEval(
            agent,
            mode=mode,
            model_profile='synthetic-title-model'
            if double
            else 'configured-title-profile',
        )

    if selector == ProcessMentorResponseEval.selector:
        answer_model = (
            SyntheticEvalModel('mentor-attachment-answer') if double else None
        )
        reviewer_model = SyntheticEvalModel('mentor-reviewer') if double else None
        answer_agent, reviewer_agent = build_process_mentor_response_eval_agents(
            settings,
            answer_model=answer_model,
            reviewer_model=reviewer_model,
        )
        return ProcessMentorResponseEval(
            answer_agent,
            reviewer_agent,
            mode=mode,
            model_profile=(
                'synthetic-answer-and-reviewer-models'
                if double
                else 'configured-answer-and-reviewer-profiles'
            ),
        )

    if selector == PrepareMentorAttachmentEval.selector:
        model = SyntheticEvalModel('mentor-attachment-vision') if double else None
        agent = build_mentor_attachment_vision_eval_agent(settings, model=model)
        return PrepareMentorAttachmentEval(
            agent,
            mode=mode,
            model_profile='synthetic-vision-model'
            if double
            else 'configured-vision-profile',
        )

    if selector == EvaluateCodeActivityEval.selector:
        client: httpx.Client
        if double:
            client = httpx.Client(
                transport=httpx.MockTransport(_synthetic_jev_response)
            )
            settings = settings.model_copy(
                update={'openrouter_api_key': 'synthetic-eval-only'}
            )
        else:
            client = httpx.Client()
        try:
            provider = build_code_rubric_eval_provider(settings, client=client)
        except Exception:
            client.close()
            raise
        return EvaluateCodeActivityEval(
            provider,
            mode=mode,
            model_profile=(
                'synthetic-jev-rubric-model' if double else 'configured-jev-profile'
            ),
            close_resources=client.close,
        )

    raise ValueError('Unknown synthetic eval selector')


def _synthetic_jev_response(request: httpx.Request) -> httpx.Response:
    try:
        payload = json.loads(request.content)
    except (json.JSONDecodeError, TypeError):
        return httpx.Response(400, json={'error': 'invalid_synthetic_request'})
    questions = payload.get('questions') if isinstance(payload, dict) else None
    state = payload.get('state') if isinstance(payload, dict) else None
    prompt = state.get('prompt', '') if isinstance(state, dict) else ''
    if not isinstance(questions, dict):
        return httpx.Response(400, json={'error': 'invalid_synthetic_request'})

    answers: dict[str, dict[str, str]] = {}
    for question_id, question in questions.items():
        criteria = question.get('criteria') if isinstance(question, dict) else None
        if not isinstance(criteria, dict) or not criteria:
            return httpx.Response(400, json={'error': 'invalid_synthetic_request'})
        if 'insufficient evidence' in prompt.casefold():
            choice = next(
                (key for key in criteria if key.endswith('-inconclusive')),
                next(iter(criteria)),
            )
        else:
            choice = next(
                (key for key in criteria if key.endswith('-75')),
                next(iter(criteria)),
            )
        answers[str(question_id)] = {'type': 'choice', 'choice': choice}
    return httpx.Response(200, json={'answers': answers}, request=request)
