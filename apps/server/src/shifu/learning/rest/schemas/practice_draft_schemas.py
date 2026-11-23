from typing import Annotated

from fastapi import Path
from pydantic import BaseModel, Field

from shifu.learning.core.domain.enums import PracticePhotoState

ID_PATTERN = r'^[0-9A-Z]{26}$'
RECORD_KEY_PATTERN = r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$'

GoalIdPath = Annotated[str, Path(pattern=ID_PATTERN)]
SkillIdPath = Annotated[str, Path(pattern=ID_PATTERN)]
CompetencyIdPath = Annotated[str, Path(pattern=ID_PATTERN)]
ActivityIdPath = Annotated[str, Path(pattern=ID_PATTERN)]
RecordKeyPath = Annotated[str, Path(pattern=RECORD_KEY_PATTERN)]

PRACTICE_DRAFT_PATH = (
    '/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}'
    '/activities/{activity_id}/practice-draft'
)


class PracticeDraftSchemas:
    class Photo(BaseModel):
        record_key: str
        photo_id: str
        state: PracticePhotoState
        media_type: str
        size_bytes: int

    class Draft(BaseModel):
        revision: int
        reflection: str
        photos: list['PracticeDraftSchemas.Photo']

    class ReflectionRequest(BaseModel):
        reflection: Annotated[str, Field(max_length=4000)]
