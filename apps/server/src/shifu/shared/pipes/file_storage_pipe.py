from fastapi import Request

from shifu.shared.core.interfaces import FileStorageProvider
from shifu.shared.providers.s3_file_storage_provider import (
    S3FileStorageProvider,
    S3FileStorageSettings,
)


class FileStoragePipe:
    @staticmethod
    def create_file_storage_provider(
        settings: S3FileStorageSettings,
    ) -> S3FileStorageProvider:
        return S3FileStorageProvider(settings)

    @staticmethod
    def get_file_storage_provider(request: Request) -> FileStorageProvider:
        return request.app.state.file_storage_provider
