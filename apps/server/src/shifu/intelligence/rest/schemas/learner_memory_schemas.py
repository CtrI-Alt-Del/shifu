from datetime import datetime

from pydantic import AliasPath, BaseModel, Field

from shifu.intelligence.core.domain.enums import LearnerMemoryCategory


class LearnerMemorySchemas:
    """Transport shape of a learner memory, read from ``LearnerMemoryDetails``."""

    class Origin(BaseModel):
        session_id: str
        message_id: str | None
        conversation_title: str | None
        is_available: bool
        declared_at: datetime

    class Concept(BaseModel):
        key: str
        label: str

    class Memory(BaseModel):
        id: str = Field(validation_alias=AliasPath('memory', 'id'))
        category: LearnerMemoryCategory = Field(
            validation_alias=AliasPath('memory', 'category')
        )
        content: str = Field(validation_alias=AliasPath('memory', 'content'))
        version: int = Field(validation_alias=AliasPath('memory', 'version'))
        created_at: datetime = Field(validation_alias=AliasPath('memory', 'created_at'))
        updated_at: datetime = Field(validation_alias=AliasPath('memory', 'updated_at'))
        origins: list['LearnerMemorySchemas.Origin']
        concepts: list['LearnerMemorySchemas.Concept']
