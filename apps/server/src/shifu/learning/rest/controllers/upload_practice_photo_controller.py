from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Request as FastApiRequest,
    Response as FastApiResponse,
    UploadFile,
)
from pydantic import UUID4, TypeAdapter

from shifu.learning.core.domain.errors import (
    PracticePhotoInvalidError,
    PracticePhotoTooLargeError,
)
from shifu.learning.core.domain.structures import PracticePhotoUpload
from shifu.learning.core.interfaces import (
    LearningDatabase,
    PracticePhotoInspectorProvider,
)
from shifu.learning.core.use_cases import UploadPracticePhotoUseCase
from shifu.learning.core.use_cases.upload_practice_photo_use_case import (
    MAX_PHOTO_BYTES,
)
from shifu.learning.pipes import LearningPipe
from shifu.learning.rest.schemas.practice_draft_schemas import (
    PRACTICE_DRAFT_PATH,
    ActivityIdPath,
    CompetencyIdPath,
    GoalIdPath,
    PracticeDraftSchemas,
    RecordKeyPath,
    SkillIdPath,
)
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    FileStorageProvider,
    IdentifierProvider,
)
from shifu.shared.pipes import AuthenticationPipe

_MAX_MULTIPART_SIZE = MAX_PHOTO_BYTES + 64_000


class Response(PracticeDraftSchemas.Draft):
    pass


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class UploadPracticePhotoController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.put(
            f'{PRACTICE_DRAFT_PATH}/photos/{{record_key}}',
            response_model=Response,
            status_code=200,
        )
        def _(
            goal_id: GoalIdPath,
            skill_id: SkillIdPath,
            competency_id: CompetencyIdPath,
            activity_id: ActivityIdPath,
            record_key: RecordKeyPath,
            request: FastApiRequest,
            http_response: FastApiResponse,
            file: Annotated[UploadFile, File()],
            upload_key: Annotated[UUID4, Form()],
            user: Annotated[
                AuthenticatedUser,
                Depends(AuthenticationPipe.get_authenticated_user),
            ],
            database: Annotated[
                LearningDatabase,
                Depends(LearningPipe.get_database),
            ],
            provider: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
            identifiers: Annotated[
                IdentifierProvider,
                Depends(LearningPipe.get_identifier_provider),
            ],
            clock: Annotated[
                ClockProvider,
                Depends(LearningPipe.get_clock_provider),
            ],
            storage: Annotated[
                FileStorageProvider,
                Depends(LearningPipe.get_practice_photo_storage_provider),
            ],
            inspector: Annotated[
                PracticePhotoInspectorProvider,
                Depends(LearningPipe.get_practice_photo_inspector_provider),
            ],
        ) -> Response:
            length = request.headers.get('content-length')
            if length is not None:
                if not length.isdecimal():
                    raise PracticePhotoInvalidError
                if int(length) > _MAX_MULTIPART_SIZE:
                    raise PracticePhotoTooLargeError

            content = file.file.read(MAX_PHOTO_BYTES + 1)
            view = UploadPracticePhotoUseCase(
                database, provider, identifiers, clock, storage, inspector
            ).execute(
                user.account_id,
                goal_id,
                skill_id,
                competency_id,
                activity_id,
                record_key,
                str(upload_key),
                PracticePhotoUpload(
                    filename=file.filename or '',
                    media_type=file.content_type or '',
                    content=content,
                ),
            )
            http_response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(view, from_attributes=True)
