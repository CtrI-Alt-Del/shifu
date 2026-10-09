from typing import Protocol


class GenerateMentorTitleWorkflow(Protocol):
    def generate(self, first_message: str) -> str: ...
