from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import pytest

from shifu.intelligence.core.domain.entities import MentorMessage, MentorSession
from shifu.intelligence.core.domain.enums import MentorMessageRole
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.database.sqlalchemy.mappers import MentorSessionMapper
from shifu.intelligence.database.sqlalchemy.models import MentorSessionModel
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.postgres_fixture import PostgresDatabase


class TestMentorPersistenceAdapters:
    def test_should_reject_mapping_a_tombstoned_session(self) -> None:
        deleted_at = datetime.now(UTC)
        tombstone = MentorSessionModel(
            id='01J7T8AC91Z5K8M4JQ8C2D6F0B',
            account_id='01J7T8AC91Z5K8M4JQ8C2D6F0C',
            submission_key='a1d61118-477e-49e9-8f67-4b9f01045083',
            content_fingerprint=None,
            title=None,
            title_search=None,
            created_at=None,
            updated_at=None,
            last_activity_at=None,
            deleted_at=deleted_at,
        )

        with pytest.raises(
            ValueError, match='A deleted Mentor session cannot be mapped as active'
        ):
            MentorSessionMapper.to_domain(tombstone)

    def test_should_find_learner_message_and_its_response(
        self, postgres_database: PostgresDatabase
    ) -> None:
        identifiers = SystemIdentifierProvider()
        account_id = identifiers.generate()
        session_id = identifiers.generate()
        learner_message_id = identifiers.generate()
        response_id = identifiers.generate()
        timestamp = datetime.now(UTC)
        database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)

        with database.transaction() as repositories:
            repositories.mentor_sessions.add(
                MentorSession(
                    id=session_id,
                    account_id=account_id,
                    title='Conversa de persistência',
                    created_at=timestamp,
                    updated_at=timestamp,
                    last_activity_at=timestamp,
                ),
                str(uuid4()),
                sha256(b'first message').hexdigest(),
            )
            repositories.mentor_messages.add(
                MentorMessage(
                    id=learner_message_id,
                    session_id=session_id,
                    role=MentorMessageRole.LEARNER,
                    content='Primeira pergunta.',
                    created_at=timestamp,
                    in_reply_to_message_id=None,
                )
            )
            repositories.mentor_messages.add(
                MentorMessage(
                    id=response_id,
                    session_id=session_id,
                    role=MentorMessageRole.MENTOR,
                    content='Resposta persistida.',
                    created_at=timestamp,
                    in_reply_to_message_id=learner_message_id,
                )
            )

            learner_message = repositories.mentor_messages.find_by_id(
                account_id, session_id, learner_message_id
            )
            response = repositories.mentor_messages.find_response(
                account_id, session_id, learner_message_id
            )

        assert learner_message is not None
        assert learner_message.content == 'Primeira pergunta.'
        assert response is not None
        assert response.id == response_id
        assert response.in_reply_to_message_id == learner_message_id
