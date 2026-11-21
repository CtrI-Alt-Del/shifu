import re
from typing import ClassVar

from shifu.communication.core.domain.errors import InvalidPushSubscriptionError
from shifu.shared.core.domain.errors import AppError, ValidationError
from shifu.shared.core.domain.structures.structure import structure


@structure
class TrustedPushEndpoint:
    """A push subscription address that belongs to a known browser push service.

    The server later sends a request to this address, so it is read from the raw
    text instead of a URL parser: parsers disagree on backslashes, user info and
    percent signs, and a disagreement would let another host receive the request.
    """

    EXACT_HOSTS: ClassVar[frozenset[str]] = frozenset(
        {'fcm.googleapis.com', 'updates.push.services.mozilla.com'}
    )
    SUFFIX_DOMAINS: ClassVar[tuple[str, ...]] = (
        'push.apple.com',
        'notify.windows.com',
    )
    _SCHEME: ClassVar[str] = 'https://'
    _AUTHORITY_END: ClassVar[re.Pattern[str]] = re.compile(r'[/?#]')
    _AUTHORITY: ClassVar[re.Pattern[str]] = re.compile(r'[a-z0-9.-]+(?::443)?')
    _LABEL: ClassVar[re.Pattern[str]] = re.compile(r'[a-z0-9]([a-z0-9-]*[a-z0-9])?')

    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str or not self.value.startswith(self._SCHEME):
            raise ValidationError
        remainder = self.value[len(self._SCHEME) :]
        authority = self._AUTHORITY_END.split(remainder, maxsplit=1)[0]
        if not self._AUTHORITY.fullmatch(authority):
            raise ValidationError
        host = authority.removesuffix(':443')
        if not all(self._LABEL.fullmatch(label) for label in host.split('.')):
            raise ValidationError
        if host not in self.EXACT_HOSTS and not any(
            host.endswith(f'.{domain}') for domain in self.SUFFIX_DOMAINS
        ):
            raise ValidationError

    @classmethod
    def create(
        cls,
        endpoint: str,
        *,
        error_type: type[AppError] = InvalidPushSubscriptionError,
    ) -> 'TrustedPushEndpoint':
        try:
            return cls(value=endpoint)
        except ValidationError as error:
            raise error_type() from error
