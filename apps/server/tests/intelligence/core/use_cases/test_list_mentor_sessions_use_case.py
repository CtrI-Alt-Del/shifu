from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.errors import MentorCursorInvalidError
from shifu.intelligence.core.domain.structures import MentorSessionsPage
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases import ListMentorSessionsUseCase


class TestListMentorSessionsUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.repositories.mentor_sessions.find_many.return_value = MentorSessionsPage(
            items=[], next_cursor=None
        )
        self.subject = ListMentorSessionsUseCase(self.database)

    def test_should_normalize_search_and_forward_cursor(self) -> None:
        result = self.subject.execute('account', '  ÁRVORES Café  ', 'cursor-value')

        assert result == MentorSessionsPage(items=[], next_cursor=None)
        self.repositories.mentor_sessions.find_many.assert_called_once_with(
            'account', '  arvores cafe  ', 'cursor-value'
        )

    @pytest.mark.parametrize('error', [ValueError('Invalid cursor'), TypeError('x')])
    def test_should_translate_a_rejected_cursor_into_a_domain_validation_error(
        self, error: Exception
    ) -> None:
        self.repositories.mentor_sessions.find_many.side_effect = error

        with pytest.raises(MentorCursorInvalidError) as raised:
            self.subject.execute('account', None, 'not-a-cursor')

        assert raised.value.message == 'Cursor inválido.'
        assert raised.value.__cause__ is error

    def test_should_not_hide_unrelated_value_errors_when_no_cursor_was_sent(
        self,
    ) -> None:
        self.repositories.mentor_sessions.find_many.side_effect = ValueError('boom')

        with pytest.raises(ValueError, match='boom'):
            self.subject.execute('account', None, None)
