from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from agno.models.base import Model
from agno.models.response import ModelResponse

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator


class SyntheticEvalModel(Model):
    """Deterministic in-process model double used only by synthetic evals."""

    def __init__(self, profile: str) -> None:
        super().__init__(id=f'shifu-synthetic-{profile}', name='Shifu Synthetic Eval')
        self._profile = profile

    def invoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        messages = kwargs.get('messages')
        if messages is None and args:
            messages = args[0]
        user_text = self._user_text(messages)
        response_format = kwargs.get('response_format')
        payload = self._payload(user_text, response_format)
        return ModelResponse(
            role='assistant',
            content=json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
        )

    def invoke_stream(self, *args: Any, **kwargs: Any) -> Iterator[ModelResponse]:
        yield self.invoke(*args, **kwargs)

    async def ainvoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        return self.invoke(*args, **kwargs)

    async def ainvoke_stream(
        self, *args: Any, **kwargs: Any
    ) -> AsyncIterator[ModelResponse]:
        yield self.invoke(*args, **kwargs)

    def _parse_provider_response(self, response: Any, **_kwargs: Any) -> ModelResponse:
        if isinstance(response, ModelResponse):
            return response
        return ModelResponse(role='assistant', content=str(response))

    def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
        return self._parse_provider_response(response)

    def _payload(self, user_text: str, response_format: Any) -> dict[str, Any]:
        schema_name = getattr(response_format, '__name__', '')
        if self._profile == 'mentor-title' or schema_name == 'MentorTitleOutput':
            return {'title': 'Frações equivalentes'}

        if (
            self._profile == 'mentor-attachment-vision'
            or schema_name == 'MentorAttachmentVisionOutput'
        ):
            illegible = 'synthetic-illegible-page' in user_text
            return {
                'legible': not illegible,
                'description': ''
                if illegible
                else 'A página mostra que 1/2 é equivalente a 2/4.',
            }

        if (
            self._profile == 'mentor-attachment-answer'
            or schema_name == 'MentorAttachmentAnswerOutput'
        ):
            source = self._first_allowed_source(user_text)
            return {
                'answer': 'A página mostra que 1/2 é equivalente a 2/4.',
                'sources': [source],
            }

        if self._profile == 'mentor-reviewer' or schema_name == 'MentorReviewOutput':
            rejected = '3/4' in user_text and '1/2' in user_text
            fields = getattr(response_format, 'model_fields', {})
            names = tuple(fields) or (
                'request_adherence',
                'fact_fidelity',
                'cumulative_solution',
                'diagnostic_safety',
                'privacy_access',
                'official_action_claims',
            )
            return {
                name: {
                    'choice': 'rejected'
                    if rejected and name == 'fact_fidelity'
                    else 'approved',
                    'feedback': 'Synthetic decision.',
                }
                for name in names
            }

        return {}

    @staticmethod
    def _user_text(messages: Any) -> str:
        if not isinstance(messages, (list, tuple)):
            return ''
        return '\n'.join(
            content
            for message in messages
            if getattr(message, 'role', None) == 'user'
            and isinstance((content := getattr(message, 'content', None)), str)
        )

    @staticmethod
    def _first_allowed_source(user_text: str) -> dict[str, Any]:
        try:
            decoded = json.loads(user_text)
        except (json.JSONDecodeError, TypeError):
            decoded = None
        if isinstance(decoded, dict):
            allowed = decoded.get('allowed_sources')
            if isinstance(allowed, list) and allowed and isinstance(allowed[0], dict):
                source = allowed[0]
                return {
                    'attachment_id': source.get(
                        'attachment_id', '01ARZ3NDEKTSV4RRFFQ69G5FAV'
                    ),
                    'chunk_id': source.get('chunk_id', '01ARZ3NDEKTSV4RRFFQ69G5FAW'),
                    'page_number': source.get('page_number', 1),
                    'locator': source.get('locator', 'page:1'),
                }
        return {
            'attachment_id': '01ARZ3NDEKTSV4RRFFQ69G5FAV',
            'chunk_id': '01ARZ3NDEKTSV4RRFFQ69G5FAW',
            'page_number': 1,
            'locator': 'page:1',
        }
