import re
from collections.abc import Mapping
from typing import Literal, Protocol, cast

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from pydantic import HttpUrl, SecretStr

from shifu.shared.core.domain.errors import ServiceUnavailableError

_OBJECT_KEY = re.compile(r'^[A-Za-z0-9][A-Za-z0-9!_.*\'()/ -]{0,510}$')
_MEDIA_TYPE = re.compile(r'^[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+$')
_UNAVAILABLE = 'O armazenamento de arquivos está temporariamente indisponível.'


class S3FileStorageSettings(Protocol):
    @property
    def mentor_attachment_storage_bucket(self) -> str: ...

    @property
    def mentor_attachment_storage_region(self) -> str: ...

    @property
    def mentor_attachment_storage_endpoint_url(self) -> HttpUrl | None: ...

    @property
    def mentor_attachment_storage_addressing_style(
        self,
    ) -> Literal['auto', 'path', 'virtual']: ...

    @property
    def mentor_attachment_storage_access_key(self) -> str | SecretStr | None: ...

    @property
    def mentor_attachment_storage_secret_key(self) -> str | SecretStr | None: ...


class _StreamingBody(Protocol):
    def read(self) -> bytes: ...

    def close(self) -> None: ...


class _S3Client(Protocol):
    def put_object(self, **kwargs: object) -> object: ...

    def get_object(self, **kwargs: object) -> Mapping[str, object]: ...

    def delete_object(self, **kwargs: object) -> object: ...

    def close(self) -> None: ...


class S3FileStorageProvider:
    def __init__(
        self,
        settings: S3FileStorageSettings,
        client: BaseClient | None = None,
    ) -> None:
        bucket = settings.mentor_attachment_storage_bucket.strip()
        if not bucket:
            raise ValueError('Attachment storage bucket is required')
        access_key = self._secret(settings.mentor_attachment_storage_access_key)
        secret_key = self._secret(settings.mentor_attachment_storage_secret_key)
        if bool(access_key) != bool(secret_key):
            raise ValueError('Attachment storage credentials must be paired')
        self._bucket = bucket
        self._client: _S3Client = (
            cast('_S3Client', client)
            if client is not None
            else cast(
                '_S3Client',
                boto3.client(  # pyright: ignore[reportUnknownMemberType] - boto3 has no complete client protocol stubs.
                    's3',
                    region_name=settings.mentor_attachment_storage_region,
                    endpoint_url=(
                        str(settings.mentor_attachment_storage_endpoint_url)
                        if settings.mentor_attachment_storage_endpoint_url is not None
                        else None
                    ),
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    config=Config(
                        signature_version='s3v4',
                        s3={
                            'addressing_style': settings.mentor_attachment_storage_addressing_style
                        },
                    ),
                ),
            )
        )

    def put(self, object_key: str, content: bytes, media_type: str) -> None:
        self._validate_object_key(object_key)
        if type(content) is not bytes or not _MEDIA_TYPE.fullmatch(media_type):
            raise ValueError('Invalid object content metadata')
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=object_key,
                Body=content,
                ContentType=media_type,
            )
        except Exception as error:
            raise ServiceUnavailableError(_UNAVAILABLE) from error

    def read(self, object_key: str) -> bytes:
        self._validate_object_key(object_key)
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=object_key)
            body = cast('_StreamingBody', response['Body'])
            try:
                content = body.read()
            finally:
                body.close()
        except Exception as error:
            raise ServiceUnavailableError(_UNAVAILABLE) from error
        return content

    def remove(self, object_key: str) -> None:
        self._validate_object_key(object_key)
        try:
            self._client.delete_object(Bucket=self._bucket, Key=object_key)
        except Exception as error:
            raise ServiceUnavailableError(_UNAVAILABLE) from error

    def close(self) -> None:
        self._client.close()

    @staticmethod
    def _secret(value: str | SecretStr | None) -> str | None:
        if isinstance(value, SecretStr):
            return value.get_secret_value()
        return value

    @staticmethod
    def _validate_object_key(object_key: str) -> None:
        if (
            not object_key
            or object_key.startswith('/')
            or '\\' in object_key
            or any(part in {'.', '..'} for part in object_key.split('/'))
            or not _OBJECT_KEY.fullmatch(object_key)
        ):
            raise ValueError('Invalid object key')
