from typing import Annotated
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Response as FastApiResponse,
)

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import ReadMentorAttachmentFileUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    FileStorageProvider,
    IdentifierProvider,
    MentorAccessProvider,
)
from shifu.shared.pipes import FileStoragePipe, SharedPipe

_ID_PATTERN = r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$'


class ReadMentorAttachmentFileController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/mentor-sessions/{session_id}/attachments/{attachment_id}/file',
            response_model=None,
            response_class=FastApiResponse,
            status_code=200,
        )
        def _(
            session_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            attachment_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            identifier_provider: Annotated[
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
        ) -> FastApiResponse:
            result = ReadMentorAttachmentFileUseCase(
                database, identifier_provider, access, storage
            ).execute(user.account_id, session_id, attachment_id, preview=preview)
            disposition = 'inline' if preview else 'attachment'
            filename = quote(result.filename, safe='')
            return FastApiResponse(
                content=result.content,
                media_type=result.media_type,
                headers={
                    'Cache-Control': 'private, no-store',
                    'X-Content-Type-Options': 'nosniff',
                    'Content-Disposition': f"{disposition}; filename*=UTF-8''{filename}",
                    'Content-Length': str(len(result.content)),
                },
            )
