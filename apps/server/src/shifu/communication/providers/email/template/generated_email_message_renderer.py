from __future__ import annotations

from datetime import datetime, UTC
from html import escape
import importlib.resources
import json
import re
from typing import TYPE_CHECKING, cast

from shifu.communication.core.domain.enums import CommunicationType
from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.domain.structures import (
    EmailMessage,
    MessageTemplateValues,
)

if TYPE_CHECKING:
    from shifu.communication.core.domain.structures import MessageContent


_PLACEHOLDER_PATTERN = re.compile(r'\{\{([a-z][a-z0-9_]*)\}\}')
_TEMPLATE_PACKAGE = 'shifu.communication.providers.email.template.generated'
_TEMPLATE_NAME = 'account-confirmation'


class GeneratedEmailMessageRenderer:
    """Render the tracked HTML/manifest contract without starting a Node process."""

    def render(
        self,
        message_type: CommunicationType,
        values: MessageContent | MessageTemplateValues,
    ) -> EmailMessage:
        if message_type is not CommunicationType.ACCOUNT_CONFIRMATION:
            raise InvalidCommunicationError
        if not isinstance(values, MessageTemplateValues):
            raise InvalidCommunicationError

        html, subject, placeholders = self._load_contract()
        if placeholders != {'display_name', 'action_url', 'expires_at'}:
            raise InvalidCommunicationError

        replacement_values = {
            'display_name': escape(values.display_name),
            'action_url': escape(values.action_url, quote=True),
            'expires_at': escape(self._format_expiry(values.expires_at)),
        }
        rendered_html = _PLACEHOLDER_PATTERN.sub(
            lambda match: replacement_values[match.group(1)],
            html,
        )
        if _PLACEHOLDER_PATTERN.search(rendered_html) is not None:
            raise InvalidCommunicationError

        # The delivery use case supplies the actual recipient and idempotency key
        # after rendering. These values keep the renderer's core return contract
        # valid while never becoming part of the generated template.
        return EmailMessage(
            idempotency_key='renderer',
            to='no-reply@shifu.local',
            subject=subject,
            html=rendered_html,
        )

    @staticmethod
    def _load_contract() -> tuple[str, str, set[str]]:
        package = importlib.resources.files(_TEMPLATE_PACKAGE)
        html = package.joinpath(f'{_TEMPLATE_NAME}.html').read_text(encoding='utf-8')
        raw_manifest = package.joinpath(f'{_TEMPLATE_NAME}.manifest.json').read_text(
            encoding='utf-8'
        )
        manifest_value: object = json.loads(raw_manifest)
        if not isinstance(manifest_value, dict):
            raise InvalidCommunicationError
        manifest = cast('dict[str, object]', manifest_value)
        subject = manifest.get('subject')
        raw_placeholders = manifest.get('placeholders')
        if not isinstance(subject, str) or not isinstance(raw_placeholders, list):
            raise InvalidCommunicationError

        placeholders: set[str] = set()
        for raw_placeholder in cast('list[object]', raw_placeholders):
            if not isinstance(raw_placeholder, dict):
                raise InvalidCommunicationError
            placeholder = cast('dict[str, object]', raw_placeholder)
            name = placeholder.get('name')
            placeholder_type = placeholder.get('type')
            if not isinstance(name, str) or not isinstance(placeholder_type, str):
                raise InvalidCommunicationError
            placeholders.add(name)

        rendered_placeholders = {
            match.group(1) for match in _PLACEHOLDER_PATTERN.finditer(html)
        }
        if rendered_placeholders != placeholders:
            raise InvalidCommunicationError
        return html, subject, placeholders

    @staticmethod
    def _format_expiry(value: datetime) -> str:
        normalized = value
        if normalized.tzinfo is None:
            normalized = normalized.replace(tzinfo=UTC)
        return normalized.astimezone(UTC).strftime('%d/%m/%Y às %H:%M UTC')
