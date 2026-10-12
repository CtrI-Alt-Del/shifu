from inngest import Function, Inngest

from shifu.intelligence.core.use_cases.process_mentor_response_use_case import (
    ProcessMentorResponseUseCase,
)
from shifu.intelligence.messaging.inngest.jobs.answer_mentor_message_job import (
    AnswerMentorMessageJob,
)


class IntelligenceInngestMessaging:
    @staticmethod
    def register(
        inngest: Inngest, use_case: ProcessMentorResponseUseCase
    ) -> list[Function[None]]:
        return [AnswerMentorMessageJob.handle(inngest, use_case)]
