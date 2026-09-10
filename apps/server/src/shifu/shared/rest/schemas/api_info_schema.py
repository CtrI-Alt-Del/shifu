from pydantic import BaseModel


class ApiInfoSchema(BaseModel):
    message: str


__all__ = ["ApiInfoSchema"]
