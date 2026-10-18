from typing import Any
from unittest.mock import create_autospec

from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentContext,
    MentorResponseBlock,
    MentorRouteResult,
)
from shifu.intelligence.core.interfaces import MentorRouteProvider
from shifu.intelligence.core.use_cases.get_mentor_attachment_context_use_case import (
    GetMentorAttachmentContextUseCase,
)
from shifu.shared.core.domain.structures import MentorContextSnapshot
from shifu.shared.core.interfaces import (
    MentorCatalogProvider,
    MentorContextProvider,
)
from tests.intelligence.core.use_cases.mentor_response_test_setup import (
    MentorResponseTestSetup,
)


def context_snapshot(**changes: Any) -> MentorContextSnapshot:
    values: dict[str, Any] = {
        'goal_id': None,
        'skill_experience_id': None,
        'skill_id': None,
        'competency_id': None,
        'activity_id': None,
        'skill_completed': None,
        'diagnostic_in_progress': False,
        'facts': (),
        'eligible_references': (),
        'resolved_references': (),
        'unavailable_sources': (),
    }
    values.update(changes)
    return MentorContextSnapshot(**values)


class MentorResponsePhaseTestSetup(MentorResponseTestSetup):
    def prepare_phase(
        self, status: MentorResponseStatus = MentorResponseStatus.PROCESSING
    ) -> None:
        super().prepare(status)
        self.context = context_snapshot()
        self.context_provider = create_autospec(MentorContextProvider, instance=True)
        self.context_provider.read.return_value = self.context
        self.route_provider = create_autospec(MentorRouteProvider, instance=True)
        self.block = MentorResponseBlock(
            block_key='local-topic',
            ordinal=0,
            intent=None,
            content='Uma resposta aprovada.',
        )
        self.route_provider.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(self.block,),
            generation_requests=(),
            clarification=None,
        )
        self.catalog_provider = create_autospec(MentorCatalogProvider, instance=True)
        self.catalog_provider.search.return_value = ()
        self.catalog_provider.read_projection.return_value = ()
        self.attachment_context = MentorAttachmentContext(chunks=(), sources=())
        self.attachment_context_use_case = create_autospec(
            GetMentorAttachmentContextUseCase, instance=True
        )
        self.attachment_context_use_case.execute.return_value = self.attachment_context
        self.repositories.mentor_response_attempts.transition.return_value = True
        self.repositories.mentor_response_attempts.claim.return_value = True
        self.repositories.mentor_response_attempts.has_claim.return_value = True
        self.repositories.mentor_response_attempts.update_references.return_value = True
        self.repositories.mentor_response_events.snapshot.return_value = self.snapshot
        self.repositories.mentor_response_events.next_sequence.return_value = 2

    def prepared_local_route(self) -> None:
        self.route_provider.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(self.block,),
            generation_requests=(),
            clarification=None,
        )
