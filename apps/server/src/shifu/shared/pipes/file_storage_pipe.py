from fastapi import Request

from shifu.shared.core.interfaces import FileStorageProvider
from shifu.shared.providers.s3_file_storage_provider import (
    S3FileStorageProvider,
    S3FileStorageSettings,
)
from shifu.shared.settings import Settings


class FileStoragePipe:
    @staticmethod
    def create_file_storage_provider(settings: Settings) -> S3FileStorageProvider:
        """Build the private Mentor attachment storage from its own settings."""
        return S3FileStorageProvider(
            S3FileStorageSettings(
                bucket=settings.mentor_attachment_storage_bucket,
                region=settings.mentor_attachment_storage_region,
                endpoint_url=settings.mentor_attachment_storage_endpoint_url,
                addressing_style=settings.mentor_attachment_storage_addressing_style,
                access_key=settings.mentor_attachment_storage_access_key,
                secret_key=settings.mentor_attachment_storage_secret_key,
            )
        )

    @staticmethod
    def create_learning_practice_photo_storage_provider(
        settings: Settings,
    ) -> S3FileStorageProvider:
        """Build the private Learning practice photo storage from its own settings."""
        return S3FileStorageProvider(
            S3FileStorageSettings(
                bucket=settings.learning_practice_photo_storage_bucket,
                region=settings.learning_practice_photo_storage_region,
                endpoint_url=settings.learning_practice_photo_storage_endpoint_url,
                addressing_style=(
                    settings.learning_practice_photo_storage_addressing_style
                ),
                access_key=settings.learning_practice_photo_storage_access_key,
                secret_key=settings.learning_practice_photo_storage_secret_key,
            )
        )

    @staticmethod
    def get_file_storage_provider(request: Request) -> FileStorageProvider:
        return request.app.state.file_storage_provider
