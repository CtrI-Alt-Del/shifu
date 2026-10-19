"""Queue limits passed from application settings to module-owned AgentOS apps."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from shifu.shared.settings import Settings


@dataclass(frozen=True, slots=True)
class AgentOSQueueSettings:
    max_concurrency: int
    max_queue_depth: int
    timeout_seconds: int
    max_attempts: int = 2

    @classmethod
    def for_module(
        cls,
        module: Literal['intelligence', 'learning'],
        settings: 'Settings',
    ) -> 'AgentOSQueueSettings':
        if module == 'intelligence':
            return cls(
                max_concurrency=settings.agentos_intelligence_queue_max_concurrency,
                max_queue_depth=settings.agentos_intelligence_queue_max_depth,
                timeout_seconds=settings.agentos_intelligence_queue_timeout_seconds,
            )
        return cls(
            max_concurrency=settings.agentos_learning_queue_max_concurrency,
            max_queue_depth=settings.agentos_learning_queue_max_depth,
            timeout_seconds=settings.agentos_learning_queue_timeout_seconds,
        )
