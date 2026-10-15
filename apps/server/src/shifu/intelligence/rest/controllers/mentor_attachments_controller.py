from typing import Annotated
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Response,
    UploadFile,
    status,
)
from fastapi import (
    Request as FastApiRequest,
)
from pydantic import UUID4

from shifu.intelligence.core.domain.structures import MentorAttachmentFile
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    MentorAttachmentExtractorProvider,
)
from shifu.intelligence.core.use_cases import (
    CreateMentorAttachmentBatchUseCase,
    GetMentorAttachmentBatchUseCase,
    ReadMentorAttachmentFileUseCase,
    RemoveMentorAttachmentUseCase,
    UploadMentorAttachmentUseCase,
)
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.mentor_attachment_schemas import (
    Attachment,
    Batch,
    BatchCreated,
    CreateBatchRequest,
)
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    ClockProvider,
    FileStorageProvider,
    IdentifierProvider,
    MentorAccessProvider,
)
from shifu.shared.pipes import FileStoragePipe, SharedPipe

_MAX_FILE_SIZE = 10_000_000
_MAX_MULTIPART_SIZE = _MAX_FILE_SIZE + 64_000
_ID_PATTERN = r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$'


class MentorAttachmentsController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        MentorAttachmentsController._register_create_batch(router)
        MentorAttachmentsController._register_upload_attachment(router)
        MentorAttachmentsController._register_get_batch(router)
        MentorAttachmentsController._register_remove_attachment(router)
        MentorAttachmentsController._register_read_file(router)

    @staticmethod
    def _register_create_batch(router: APIRouter) -> None:
        @router.post(
            '/mentor-attachment-batches',
            response_model=BatchCreated,
            status_code=status.HTTP_201_CREATED,
        )
        def create_batch(
            body: CreateBatchRequest,
            response: Response,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            identifier: Annotated[
                IdentifierProvider, Depends(IntelligencePipe.get_identifier_provider)
            ],
            clock: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
            access: Annotated[
                MentorAccessProvider,
                Depends(IntelligencePipe.get_mentor_access_provider),
            ],
        ) -> BatchCreated:
            if body.session_id is not None and not _is_ulid(body.session_id):
                raise _invalid_request()
            result = CreateMentorAttachmentBatchUseCase(
                database, identifier, clock, access
            ).execute(user.account_id, body.session_id)
            response.headers['Cache-Control'] = 'private, no-store'
            return BatchCreated(batch_id=result.batch_id, expires_at=result.expires_at)

    @staticmethod
    def _register_upload_attachment(router: APIRouter) -> None:
        @router.post(
            '/mentor-attachment-batches/{batch_id}/attachments',
            response_model=Attachment,
            status_code=status.HTTP_201_CREATED,
        )
        async def upload_attachment(
            batch_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            request: FastApiRequest,
            response: Response,
            file: Annotated[UploadFile, File()],
            upload_key: Annotated[UUID4, Form()],
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            identifier: Annotated[
                IdentifierProvider, Depends(IntelligencePipe.get_identifier_provider)
            ],
            clock: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
            access: Annotated[
                MentorAccessProvider,
                Depends(IntelligencePipe.get_mentor_access_provider),
            ],
            storage: Annotated[
                FileStorageProvider,
                Depends(FileStoragePipe.get_file_storage_provider),
            ],
            extractor: Annotated[
                MentorAttachmentExtractorProvider,
                Depends(IntelligencePipe.get_mentor_attachment_extractor_provider),
            ],
        ) -> Attachment:
            if not _is_ulid(batch_id):
                raise _invalid_request()
            length = request.headers.get('content-length')
            if length is not None:
                if not length.isdecimal():
                    raise _invalid_request()
                if int(length) > _MAX_MULTIPART_SIZE:
                    raise _too_large()
            content = await file.read(_MAX_FILE_SIZE + 1)
            if len(content) > _MAX_FILE_SIZE:
                raise _too_large()
            uploaded = MentorAttachmentFile(
                filename=file.filename or '',
                media_type=file.content_type or '',
                content=content,
            )
            result = UploadMentorAttachmentUseCase(
                database, identifier, clock, access, storage, extractor
            ).execute(user.account_id, batch_id, str(upload_key), uploaded)
            response.status_code = (
                status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
            )
            response.headers['Cache-Control'] = 'private, no-store'
            return Attachment.model_validate(result.attachment, from_attributes=True)

    @staticmethod
    def _register_get_batch(router: APIRouter) -> None:
        @router.get(
            '/mentor-attachment-batches/{batch_id}',
            response_model=Batch,
        )
        def get_batch(
            batch_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            response: Response,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            clock: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
            access: Annotated[
                MentorAccessProvider,
                Depends(IntelligencePipe.get_mentor_access_provider),
            ],
        ) -> Batch:
            if not _is_ulid(batch_id):
                raise _invalid_request()
            result = GetMentorAttachmentBatchUseCase(database, clock, access).execute(
                user.account_id, batch_id
            )
            response.headers['Cache-Control'] = 'private, no-store'
            return Batch.model_validate(result, from_attributes=True)

    @staticmethod
    def _register_remove_attachment(router: APIRouter) -> None:
        @router.delete(
            '/mentor-attachment-batches/{batch_id}/attachments/{attachment_id}',
            status_code=status.HTTP_204_NO_CONTENT,
        )
        def remove_attachment(
            batch_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            attachment_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            response: Response,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            clock: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
            access: Annotated[
                MentorAccessProvider,
                Depends(IntelligencePipe.get_mentor_access_provider),
            ],
        ) -> Response:
            if not _is_ulid(batch_id) or not _is_ulid(attachment_id):
                raise _invalid_request()
            RemoveMentorAttachmentUseCase(database, clock, access).execute(
                user.account_id, batch_id, attachment_id
            )
            response.headers['Cache-Control'] = 'private, no-store'
            response.status_code = status.HTTP_204_NO_CONTENT
            return response

    @staticmethod
    def _register_read_file(router: APIRouter) -> None:
        @router.get(
            '/mentor-sessions/{session_id}/attachments/{attachment_id}/file',
            response_class=Response,
        )
        def read_file(
            session_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            attachment_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            identifier: Annotated[
                IdentifierProvider, Depends(IntelligencePipe.get_identifier_provider)
            ],
            access: Annotated[
                MentorAccessProvider,
                Depends(IntelligencePipe.get_mentor_access_provider),
            ],
            storage: Annotated[
                FileStorageProvider,
                Depends(FileStoragePipe.get_file_storage_provider),
            ],
            preview: bool = False,
        ) -> Response:
            if not _is_ulid(session_id) or not _is_ulid(attachment_id):
                raise _invalid_request()
            result = ReadMentorAttachmentFileUseCase(
                database, identifier, access, storage
            ).execute(
                user.account_id,
                session_id,
                attachment_id,
                preview=preview,
            )
            disposition = 'inline' if preview else 'attachment'
            filename = quote(result.filename, safe='')
            return Response(
                content=result.content,
                media_type=result.media_type,
                headers={
                    'Cache-Control': 'private, no-store',
                    'X-Content-Type-Options': 'nosniff',
                    'Content-Disposition': f"{disposition}; filename*=UTF-8''{filename}",
                    'Content-Length': str(len(result.content)),
                },
            )


def _is_ulid(value: str) -> bool:
    return (
        len(value) == 26
        and value[0] <= '7'
        and all(character in '0123456789ABCDEFGHJKMNPQRSTVWXYZ' for character in value)
    )


def _invalid_request() -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            'code': 'malformed_attachment',
            'message': 'O arquivo não é válido ou não está disponível.',
        },
    )


def _too_large() -> HTTPException:
    return HTTPException(
        status_code=413,
        detail={
            'code': 'attachment_too_large',
            'message': 'O arquivo excede o limite de 10 MB.',
        },
    )
