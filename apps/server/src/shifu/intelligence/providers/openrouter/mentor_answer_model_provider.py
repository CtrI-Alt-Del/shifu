from typing import ClassVar, Literal

from shifu.intelligence.ai.agno.models.mentor_openai_chat import MentorOpenAIChat
from shifu.shared.settings import Settings


class OpenrouterMentorAnswerModelProvider:
    _BASE_URL: ClassVar[str] = 'https://openrouter.ai/api/v1'
    _TIMEOUT_SECONDS: ClassVar[float] = 30.0
    _MODEL_IDS: ClassVar[dict[str, str]] = {
        'primary': 'openai/gpt-6-luna',
        'reviewer': 'openai/gpt-6-luna',
        'fallback': 'deepseek/deepseek-v4.1-flash',
    }

    @classmethod
    def build(
        cls,
        settings: Settings,
        *,
        profile: Literal['primary', 'fallback', 'reviewer'] = 'primary',
    ) -> MentorOpenAIChat | None:
        if (
            not settings.openrouter_api_key
            or not settings.openrouter_prompt_logging_disabled
        ):
            return None
        return MentorOpenAIChat(
            id=cls._MODEL_IDS[profile],
            api_key=settings.openrouter_api_key,
            base_url=cls._BASE_URL,
            timeout=cls._TIMEOUT_SECONDS,
            max_retries=0,
            retries=0,
            retry_with_guidance=False,
            retry_with_guidance_limit=0,
            strict_output=True,
            store=False,
            extra_body={
                'provider': {
                    'zdr': True,
                    'data_collection': 'deny',
                    'require_parameters': True,
                    'allow_fallbacks': False,
                }
            },
        )
