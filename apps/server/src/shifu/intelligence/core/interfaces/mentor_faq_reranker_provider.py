from typing import Protocol


class MentorFaqRerankerProvider(Protocol):
    def score(self, content: str, documents: tuple[str, ...]) -> tuple[float, ...]: ...
