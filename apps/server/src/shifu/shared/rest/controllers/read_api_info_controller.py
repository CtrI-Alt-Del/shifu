from fastapi import APIRouter

from shifu.shared.rest.schemas.api_info_schema import ApiInfoSchema


class ReadApiInfoController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get("/", response_model=ApiInfoSchema, status_code=200)
        def read_api_info() -> ApiInfoSchema:
            return ApiInfoSchema(message="Shifu API")


__all__ = ["ReadApiInfoController"]
