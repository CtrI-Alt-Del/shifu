"""Support for the Learning Mentor action route tests: an application bound to the
disposable PostgreSQL database, controlled authentication and outbox/receipt reads."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, ClassVar, cast

from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select

from shifu.app import FastAPIApp
from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.learning.database.sqlalchemy.models import (
    MentorActionReceiptModel,
    SkillExperienceModel,
)
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.sqlalchemy.models import EventModel

if TYPE_CHECKING:
    from collections.abc import Generator

    from httpx import Response

RESOLVED_EVENT_NAME = 'learning/mentor-skill-action-resolved'


class MentorActionFixture:
    _ids: ClassVar[IdProviderFaker] = IdProviderFaker()
    ACCOUNT_ID: ClassVar[str] = _ids.generate()
    OTHER_ACCOUNT_ID: ClassVar[str] = _ids.generate()
    OWNER_HEADERS: ClassVar[dict[str, str]] = {'Authorization': 'Bearer owner-token'}
    OTHER_HEADERS: ClassVar[dict[str, str]] = {'Authorization': 'Bearer other-token'}
    INACTIVE_HEADERS: ClassVar[dict[str, str]] = {
        'Authorization': 'Bearer inactive-token'
    }

    @staticmethod
    def new_id() -> str:
        return MentorActionFixture._ids.generate()

    @staticmethod
    def create_client(engine: Engine) -> TestClient:
        """Build an independent application and client over the shared engine."""

        app = FastAPIApp.register(engine)
        app.state.authentication_provider = _Authentication()
        app.state.inngest_broker = _NoopBroker()
        return TestClient(app, raise_server_exceptions=False)

    @staticmethod
    @contextmanager
    def client(engine: Engine) -> Generator[TestClient]:
        with MentorActionFixture.create_client(engine) as client:
            yield client

    @staticmethod
    def post(
        client: TestClient,
        path: str,
        body: dict[str, object],
        headers: dict[str, str] | None = None,
    ) -> Response:
        return cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                path,
                json=body,
                headers=headers
                if headers is not None
                else MentorActionFixture.OWNER_HEADERS,
            ),
        )

    @staticmethod
    def count_receipts(engine: Engine) -> int:
        with engine.connect() as connection:
            return (
                connection.scalar(
                    select(func.count()).select_from(MentorActionReceiptModel)
                )
                or 0
            )

    @staticmethod
    def count_experiences(engine: Engine, goal_id: str | None = None) -> int:
        statement = select(func.count()).select_from(SkillExperienceModel)
        if goal_id is not None:
            statement = statement.where(SkillExperienceModel.goal_id == goal_id)
        with engine.connect() as connection:
            return connection.scalar(statement) or 0

    @staticmethod
    def resolved_events(engine: Engine) -> list[dict[str, object]]:
        with engine.connect() as connection:
            rows = connection.scalars(
                select(EventModel.payload)
                .where(EventModel.name == RESOLVED_EVENT_NAME)
                .order_by(EventModel.created_at)
            ).all()
        return list(rows)


class _Authentication:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        accounts = {
            'owner-token': MentorActionFixture.ACCOUNT_ID,
            'other-token': MentorActionFixture.OTHER_ACCOUNT_ID,
        }
        account_id = accounts.get(access_token)
        if account_id is None:
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=account_id,
            display_name='Pessoa Aprendente',
            time_zone=None,
        )


class _NoopBroker:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
