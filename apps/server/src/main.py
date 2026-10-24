import uvicorn

from shifu.app import app as app
from shifu.shared.constants import ENVIRONMENT
from shifu.shared.providers.console_telemetry_provider import (
    configure_telemetry_logging,
)


configure_telemetry_logging(
    app.state.telemetry_provider,
    log_level=ENVIRONMENT.server_log_level,
)


if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host='0.0.0.0',  # noqa: S104 - Compose Inngest reaches the host API.
        port=ENVIRONMENT.server_app_port,
        reload=True,
        proxy_headers=False,
        log_config=None,
    )
