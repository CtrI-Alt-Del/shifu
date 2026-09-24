from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage as SmtpMessage
from importlib import import_module
import re
from typing import TYPE_CHECKING, cast

from shifu.communication.core.domain.structures import DeliveryOutcome, EmailMessage

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Protocol

    class _AioSmtplibModule(Protocol):
        send: Callable[..., Awaitable[object]]


class SmtpEmailDeliveryProvider:
    """Send one message through a bounded SMTP attempt, normally Mailpit locally."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
        timeout_seconds: float = 10.0,
        start_tls: bool = False,
        use_tls: bool = False,
    ) -> None:
        self._host = host
        self._port = port
        self._sender = sender
        self._username = username
        self._password = password
        self._timeout_seconds = timeout_seconds
        self._start_tls = start_tls
        self._use_tls = use_tls

    def send(self, message: EmailMessage) -> DeliveryOutcome:
        smtp_message = SmtpMessage()
        smtp_message['From'] = self._sender
        smtp_message['To'] = message.to
        smtp_message['Subject'] = message.subject
        text_body = message.text or self._text_from_html(message.html)
        smtp_message.set_content(text_body)
        smtp_message.add_alternative(message.html, subtype='html')
        try:
            self._run_send(smtp_message)
        except Exception as error:  # noqa: BLE001 - provider boundary maps safely.
            return self._map_error(error)
        return DeliveryOutcome.accepted()

    def _run_send(self, message: SmtpMessage) -> None:
        async def send_message() -> None:
            module = cast('_AioSmtplibModule', import_module('aiosmtplib'))
            send = module.send
            options: dict[str, object] = {
                'hostname': self._host,
                'port': self._port,
                'timeout': self._timeout_seconds,
                'start_tls': self._start_tls,
                'use_tls': self._use_tls,
            }
            if self._username is not None:
                options['username'] = self._username
            if self._password is not None:
                options['password'] = self._password
            await send(message, **options)

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(send_message())
            return
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(asyncio.run, send_message()).result()

    @staticmethod
    def _map_error(error: Exception) -> DeliveryOutcome:
        code = getattr(error, 'code', None)
        if isinstance(code, int):
            if code >= 500:
                return DeliveryOutcome.permanent_failure('smtp_permanent_rejection')
            if code >= 400:
                return DeliveryOutcome.temporary_failure('smtp_temporary_failure')
        if isinstance(error, TimeoutError):
            return DeliveryOutcome.permanent_failure('smtp_acceptance_unknown')
        return DeliveryOutcome.temporary_failure('smtp_connection_failed')

    @staticmethod
    def _text_from_html(html: str) -> str:
        return re.sub(r'<[^>]*>', ' ', html).replace('&nbsp;', ' ').strip()
