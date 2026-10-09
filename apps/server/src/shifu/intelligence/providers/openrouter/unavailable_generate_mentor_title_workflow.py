from shifu.intelligence.core.domain.errors import MentorTitleUnavailableError


class UnavailableGenerateMentorTitleWorkflow:
    def generate(self, first_message: str) -> str:
        del first_message
        raise MentorTitleUnavailableError
