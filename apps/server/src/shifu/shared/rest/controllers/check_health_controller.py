from fastapi import APIRouter
from pydantic import BaseModel


class Response(BaseModel):
    status: str
    name: str


class CheckHealthController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get('/health', response_model=Response, status_code=200)
        def _() -> Response:
            return Response(status='ok', name='Shifu API')
