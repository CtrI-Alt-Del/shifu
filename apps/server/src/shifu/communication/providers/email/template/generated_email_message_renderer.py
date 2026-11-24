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
    AccountErasureOperationalAlertValues,
    EmailMessage,
    MessageTemplateValues,
)

if TYPE_CHECKING:
    from shifu.communication.core.domain.structures import MessageContent


_PLACEHOLDER_PATTERN = re.compile(r'\{\{([a-z][a-z0-9_]*)\}\}')
_TEMPLATE_PACKAGE = 'shifu.communication.providers.email.template.generated'
_TEMPLATE_NAMES = {
    CommunicationType.ACCOUNT_CONFIRMATION: 'account-confirmation',
    CommunicationType.PASSWORD_RECOVERY: 'password-recovery',
    CommunicationType.ACCOUNT_ERASURE_ALERT: 'account-erasure-alert',
}


class GeneratedEmailMessageRenderer:
    """Render the tracked HTML/manifest contract without starting a Node process."""

    def render(
        self,
        message_type: CommunicationType,
        values: (
            MessageContent
            | MessageTemplateValues
            | AccountErasureOperationalAlertValues
        ),
    ) -> EmailMessage:
        template_name = _TEMPLATE_NAMES.get(message_type)
        if template_name is None:
            raise InvalidCommunicationError

        html, text, subject, placeholders = self._load_contract(template_name)
        expected_placeholders, replacement_values = self._replacement_values(
            message_type,
            values,
        )
        if placeholders != expected_placeholders:
            raise InvalidCommunicationError

        rendered_html = _PLACEHOLDER_PATTERN.sub(
            lambda match: replacement_values[match.group(1)],
            html,
        )
        if _PLACEHOLDER_PATTERN.search(rendered_html) is not None:
            raise InvalidCommunicationError
        rendered_text = None
        if text is not None:
            rendered_text = _PLACEHOLDER_PATTERN.sub(
                lambda match: replacement_values[match.group(1)],
                text,
            )
            if _PLACEHOLDER_PATTERN.search(rendered_text) is not None:
                raise InvalidCommunicationError

        # The delivery use case supplies the actual recipient and idempotency key
        # after rendering. These values keep the renderer's core return contract
        # valid while never becoming part of the generated template.
        return EmailMessage(
            idempotency_key='renderer',
            to='no-reply@shifu.local',
            subject=subject,
            html=rendered_html,
            text=rendered_text,
        )

    @classmethod
    def _replacement_values(
        cls,
        message_type: CommunicationType,
        values: MessageContent
        | MessageTemplateValues
        | AccountErasureOperationalAlertValues,
    ) -> tuple[set[str], dict[str, str]]:
        if message_type is CommunicationType.ACCOUNT_ERASURE_ALERT:
            if not isinstance(values, AccountErasureOperationalAlertValues):
                raise InvalidCommunicationError
            expected_placeholders = {
                'erasure_id',
                'module',
                'failure_code',
                'closed_at',
                'due_at',
            }
            replacement_values = {
                'erasure_id': escape(str(values.erasure_id)),
                'module': escape(values.module),
                'failure_code': escape(values.failure_code),
                'closed_at': escape(cls._format_timestamp(values.closed_at)),
                'due_at': escape(cls._format_timestamp(values.due_at)),
            }
            return expected_placeholders, replacement_values

        if not isinstance(values, MessageTemplateValues):
            raise InvalidCommunicationError

        expected_placeholders = (
            {'display_name', 'action_url', 'expires_at'}
            if message_type is CommunicationType.ACCOUNT_CONFIRMATION
            else {'action_url', 'expires_at'}
        )
        if message_type is CommunicationType.ACCOUNT_CONFIRMATION:
            if values.display_name is None:
                raise InvalidCommunicationError
        elif values.display_name is not None:
            raise InvalidCommunicationError

        replacement_values = {
            'action_url': escape(values.action_url, quote=True),
            'expires_at': escape(cls._format_expiry(values.expires_at)),
        }
        if values.display_name is not None:
            replacement_values['display_name'] = escape(values.display_name)
        return expected_placeholders, replacement_values

    @staticmethod
    def _load_contract(template_name: str) -> tuple[str, str | None, str, set[str]]:
        package = importlib.resources.files(_TEMPLATE_PACKAGE)
        html = package.joinpath(f'{template_name}.html').read_text(encoding='utf-8')
        raw_manifest = package.joinpath(f'{template_name}.manifest.json').read_text(
            encoding='utf-8'
        )
        manifest_value: object = json.loads(raw_manifest)
        if not isinstance(manifest_value, dict):
            raise InvalidCommunicationError
        manifest = cast('dict[str, object]', manifest_value)
        subject = manifest.get('subject')
        text_value = manifest.get('text')
        text = text_value if isinstance(text_value, str) else None
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
        if text is not None:
            text_placeholders = {
                match.group(1) for match in _PLACEHOLDER_PATTERN.finditer(text)
            }
            if text_placeholders != placeholders:
                raise InvalidCommunicationError
        return html, text, subject, placeholders

    @staticmethod
    def _format_expiry(value: datetime) -> str:
        normalized = value
        if normalized.tzinfo is None:
            normalized = normalized.replace(tzinfo=UTC)
        return normalized.astimezone(UTC).strftime('%d/%m/%Y às %H:%M UTC')

    @staticmethod
    def _format_timestamp(value: datetime) -> str:
        return value.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')
