from pydantic import BaseModel, ConfigDict, Field, field_validator

from shifu.intelligence.core.domain.structures.mentor_page import MENTOR_PAGE_LABELS


class MentorContextHintSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')
    goal_id: str | None = Field(default=None, pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')
    skill_id: str | None = Field(default=None, pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')
    competency_id: str | None = Field(
        default=None, pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$'
    )
    material_id: str | None = Field(
        default=None, pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$'
    )
    activity_id: str | None = Field(
        default=None, pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$'
    )
    page: str | None = Field(default=None, max_length=40)
    question: str | None = Field(
        default=None, max_length=64, pattern=r'^[A-Za-z0-9_-]+$'
    )

    @field_validator('page')
    @classmethod
    def known_page(cls, page: str | None) -> str | None:
        if page is not None and page not in MENTOR_PAGE_LABELS:
            message = 'Unknown page'
            raise ValueError(message)
        return page
