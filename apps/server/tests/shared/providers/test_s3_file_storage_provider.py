from collections.abc import Mapping
from typing import TYPE_CHECKING, Literal, cast

import pytest
from pydantic import HttpUrl, SecretStr, TypeAdapter

from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.providers.s3_file_storage_provider import (
    S3FileStorageProvider,
)

if TYPE_CHECKING:
    from botocore.client import BaseClient


class _Settings:
    mentor_attachment_storage_bucket = 'private-attachments'
    mentor_attachment_storage_region = 'sa-east-1'
    mentor_attachment_storage_endpoint_url: HttpUrl | None = None
    mentor_attachment_storage_addressing_style: Literal['auto', 'path', 'virtual'] = (
        'path'
    )
    mentor_attachment_storage_access_key: str | SecretStr | None = None
    mentor_attachment_storage_secret_key: str | SecretStr | None = None


class _Body:
    def __init__(self, content: bytes = b'private-content') -> None:
        self.content = content
        self.closed = False
        self.error: Exception | None = None

    def read(self) -> bytes:
        if self.error is not None:
            raise self.error
        return self.content

    def close(self) -> None:
        self.closed = True


class _Client:
    def __init__(self) -> None:
        self.put_calls: list[dict[str, object]] = []
        self.get_calls: list[dict[str, object]] = []
        self.delete_calls: list[dict[str, object]] = []
        self.body = _Body()
        self.put_error: Exception | None = None
        self.get_error: Exception | None = None
        self.delete_error: Exception | None = None
        self.closed = False

    def put_object(self, **kwargs: object) -> object:
        self.put_calls.append(kwargs)
        if self.put_error is not None:
            raise self.put_error
        return {}

    def get_object(self, **kwargs: object) -> Mapping[str, object]:
        self.get_calls.append(kwargs)
        if self.get_error is not None:
            raise self.get_error
        return {'Body': self.body}

    def delete_object(self, **kwargs: object) -> object:
        self.delete_calls.append(kwargs)
        if self.delete_error is not None:
            raise self.delete_error
        return {}

    def close(self) -> None:
        self.closed = True


class _CapturedConfig:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


def _provider(
    client: _Client, settings: _Settings | None = None
) -> S3FileStorageProvider:
    return S3FileStorageProvider(settings or _Settings(), cast('BaseClient', client))


def test_should_write_read_remove_and_close_private_objects() -> None:
    client = _Client()
    provider = _provider(client)

    provider.put('account-1/attachment-1/original', b'image', 'image/png')
    assert client.put_calls == [
        {
            'Bucket': 'private-attachments',
            'Key': 'account-1/attachment-1/original',
            'Body': b'image',
            'ContentType': 'image/png',
        }
    ]

    assert provider.read('account-1/attachment-1/original') == b'private-content'
    assert client.get_calls == [
        {'Bucket': 'private-attachments', 'Key': 'account-1/attachment-1/original'}
    ]
    assert client.body.closed

    provider.remove('account-1/attachment-1/original')
    assert client.delete_calls == [
        {'Bucket': 'private-attachments', 'Key': 'account-1/attachment-1/original'}
    ]

    provider.close()
    assert client.closed


@pytest.mark.parametrize(
    ('method', 'error_field'),
    [
        ('put', 'put_error'),
        ('read', 'get_error'),
        ('remove', 'delete_error'),
    ],
)
def test_should_hide_storage_service_errors(
    method: str,
    error_field: str,
) -> None:
    client = _Client()
    setattr(client, error_field, RuntimeError('sensitive endpoint details'))
    provider = _provider(client)

    with pytest.raises(
        ServiceUnavailableError, match='temporariamente indisponível'
    ) as error:
        if method == 'put':
            provider.put('account-1/file', b'content', 'text/plain')
        elif method == 'read':
            provider.read('account-1/file')
        else:
            provider.remove('account-1/file')

    assert 'sensitive endpoint details' not in str(error.value)


def test_should_close_stream_when_read_fails() -> None:
    client = _Client()
    client.body.error = RuntimeError('stream failed')
    provider = _provider(client)

    with pytest.raises(ServiceUnavailableError):
        provider.read('account-1/file')

    assert client.body.closed


@pytest.mark.parametrize(
    ('object_key', 'content', 'media_type'),
    [
        ('../outside', b'x', 'text/plain'),
        ('account-1\\outside', b'x', 'text/plain'),
        ('/absolute', b'x', 'text/plain'),
        ('account-1/file', bytearray(b'x'), 'text/plain'),
        ('account-1/file', b'x', 'not-a-media-type'),
    ],
)
def test_should_reject_invalid_object_metadata_before_storage_call(
    object_key: str,
    content: bytes | bytearray,
    media_type: str,
) -> None:
    client = _Client()
    provider = _provider(client)

    with pytest.raises(ValueError):
        provider.put(object_key, content, media_type)  # type: ignore[arg-type]

    assert not client.put_calls


@pytest.mark.parametrize(
    'object_key',
    ['', '.', '..', 'account-1/./file', 'account-1/../file', 'has?query'],
)
def test_should_reject_unsafe_keys_for_reads_and_removal(object_key: str) -> None:
    client = _Client()
    provider = _provider(client)

    with pytest.raises(ValueError):
        provider.read(object_key)
    with pytest.raises(ValueError):
        provider.remove(object_key)

    assert not client.get_calls
    assert not client.delete_calls


def test_should_require_bucket_and_paired_credentials() -> None:
    empty_bucket = _Settings()
    empty_bucket.mentor_attachment_storage_bucket = ''
    with pytest.raises(ValueError, match='bucket is required'):
        S3FileStorageProvider(empty_bucket)

    settings = _Settings()
    settings.mentor_attachment_storage_access_key = 'access'
    with pytest.raises(ValueError, match='credentials must be paired'):
        S3FileStorageProvider(settings)


def test_should_build_private_s3_client_from_storage_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}
    client = _Client()

    def build_client(service: str, **kwargs: object) -> _Client:
        observed['service'] = service
        observed.update(kwargs)
        return client

    monkeypatch.setattr(
        'shifu.shared.providers.s3_file_storage_provider.boto3.client', build_client
    )
    monkeypatch.setattr(
        'shifu.shared.providers.s3_file_storage_provider.Config', _CapturedConfig
    )
    settings = _Settings()
    settings.mentor_attachment_storage_endpoint_url = TypeAdapter(
        HttpUrl
    ).validate_python('http://minio.local:9000')
    settings.mentor_attachment_storage_access_key = SecretStr('access-secret')
    settings.mentor_attachment_storage_secret_key = SecretStr('secret-secret')

    provider = S3FileStorageProvider(settings)

    assert observed['service'] == 's3'
    assert observed['region_name'] == 'sa-east-1'
    assert observed['endpoint_url'] == 'http://minio.local:9000/'
    assert observed['aws_access_key_id'] == 'access-secret'
    assert observed['aws_secret_access_key'] == 'secret-secret'
    config = cast('_CapturedConfig', observed['config'])
    assert config.kwargs == {
        'signature_version': 's3v4',
        's3': {'addressing_style': 'path'},
    }

    provider.close()
    assert client.closed
