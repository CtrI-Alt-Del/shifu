from typing import Protocol


class ActionTokenProvider(Protocol):
    def generate(self) -> str: ...

    def hash(self, token: str) -> str: ...
