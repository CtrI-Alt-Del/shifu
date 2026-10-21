from pydantic import BaseModel, ConfigDict, Field


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
