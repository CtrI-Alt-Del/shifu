from fastapi import FastAPI

from shifu.composition.router import AppRouter


def create_app() -> FastAPI:
    application = FastAPI(
        title="Shifu API",
        version="0.1.0",
    )

    application.include_router(AppRouter.register())

    return application


app = create_app()

__all__ = ["app", "create_app"]
