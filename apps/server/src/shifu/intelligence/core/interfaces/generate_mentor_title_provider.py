from typing import Protocol


class GenerateMentorTitleProvider(Protocol):
    def generate(self, first_message: str) -> str: ...
