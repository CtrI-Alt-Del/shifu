from pydantic import BaseModel


class HealthSchema(BaseModel):
    status: str


__all__ = ["HealthSchema"]
