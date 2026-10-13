from contextlib import AbstractContextManager
from typing import Protocol


class MentorTelemetryProvider(Protocol):
    def scope(self, stage: str) -> AbstractContextManager[None]: ...

    def record_inference(
        self,
        profile: str,
        used_tokens: int | None,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_usd: float | None,
    ) -> None: ...
