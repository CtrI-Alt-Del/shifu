from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Path,
    Request as FastApiRequest,
    Response as FastApiResponse,
    UploadFile,
)
from pydantic import UUID4, TypeAdapter

from shifu.intelligence.core.domain.errors import (
    MentorAttachmentInvalidError,
    MentorAttachmentTooLargeError,
)
from shifu.intelligence.core.domain.structures import MentorAttachmentFile
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    MentorAttachmentExtractorProvider,
)
from shifu.intelligence.core.use_cases import UploadMentorAttachmentUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.mentor_session_schemas import MentorSessionSchemas
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    ClockProvider,
    FileStorageProvider,
    IdentifierProvider,
    MentorAccessProvider,
)
from shifu.shared.pipes import FileStoragePipe, SharedPipe

_MAX_FILE_SIZE = 2_000_000
_MAX_MULTIPART_SIZE = _MAX_FILE_SIZE + 64_000
_ID_PATTERN = r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$'


class Response(MentorSessionSchemas.Attachment):
    pass


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class UploadMentorAttachmentController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/mentor-attachment-batches/{batch_id}/attachments',
            response_model=Response,
            status_code=201,
        )
        def _(
            batch_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            request: FastApiRequest,
            response: FastApiResponse,
            file: Annotated[UploadFile, File()],
            upload_key: Annotated[UUID4, Form()],
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            identifier_provider: Annotated[
                IdentifierProvider, Depends(IntelligencePipe.get_identifier_provider)
            ],
            clock_provider: Annotated[
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
        ) -> Response:
            length = request.headers.get('content-length')
            if length is not None:
                if not length.isdecimal():
                    raise MentorAttachmentInvalidError(
                        'O arquivo não é válido ou não está disponível.'
                    )
                if int(length) > _MAX_MULTIPART_SIZE:
                    raise MentorAttachmentTooLargeError
            content = file.file.read(_MAX_FILE_SIZE + 1)
            result = UploadMentorAttachmentUseCase(
                database,
                identifier_provider,
                clock_provider,
                access,
                storage,
                extractor,
            ).execute(
                user.account_id,
                batch_id,
                str(upload_key),
                MentorAttachmentFile(
                    filename=file.filename or '',
                    media_type=file.content_type or '',
                    content=content,
                ),
            )
            response.status_code = 201 if result.created else 200
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(
                result.attachment, from_attributes=True
            )
