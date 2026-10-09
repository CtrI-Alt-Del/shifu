from pydantic import BaseModel, ConfigDict, Field


class MentorTitleOutput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    title: str = Field(min_length=1, max_length=120)
