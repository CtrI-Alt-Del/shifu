from fastapi import APIRouter


class IdentityRouter:
    @staticmethod
    def register() -> APIRouter:
        return APIRouter(prefix="/identity", tags=["identity"])


__all__ = ["IdentityRouter"]
