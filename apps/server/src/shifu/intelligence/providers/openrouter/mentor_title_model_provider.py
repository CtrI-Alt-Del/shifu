from agno.models.base import Model
from agno.models.openai import OpenAIChat

from shifu.shared.settings import Settings


class MentorTitleModelProvider:
    _BASE_URL = 'https://openrouter.ai/api/v1'
    _MODEL_ID = 'openai/gpt-6-luna'
    _TIMEOUT_SECONDS = 3.0

    @classmethod
    def build(cls, settings: Settings) -> Model | None:
        if (
            not settings.openrouter_api_key
            or not settings.mentor_title_prompt_logging_disabled
        ):
            return None

        return OpenAIChat(
            id=cls._MODEL_ID,
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
