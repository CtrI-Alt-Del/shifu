from fastapi import APIRouter

from shifu.shared.rest.schemas.health_schema import HealthSchema


class CheckHealthController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get("/health", response_model=HealthSchema, status_code=200)
        def check_health() -> HealthSchema:
            return HealthSchema(status="ok")


__all__ = ["CheckHealthController"]
