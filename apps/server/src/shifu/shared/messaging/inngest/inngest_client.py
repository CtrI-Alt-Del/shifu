"""Construction of the process-wide Inngest client.

The SDK client is deliberately created by application composition rather than at
module import time.  This keeps importing domain modules side-effect free and
makes the local client straightforward to replace in integration tests.
"""

from logging import getLogger
from importlib import import_module

from shifu.shared.messaging.inngest.inngest_settings import InngestSettings


class InngestClient:
    @staticmethod
    def create() -> object:
        configuration = InngestSettings.from_environment()
        sdk = import_module('inngest')
        sdk_client_type = getattr(sdk, 'Inngest')  # noqa: B009 - optional SDK import
        return sdk_client_type(
            app_id=configuration.app_id,
            api_base_url=configuration.api_base_url,
            event_api_base_url=configuration.event_api_base_url,
            event_key=configuration.event_key,
            is_production=configuration.is_production,
            logger=getLogger(name='uvicorn'),
            signing_key=configuration.signing_key,
        )
