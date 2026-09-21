import logging

import uvicorn

from shifu.app import app as app
from shifu.shared.constants import ENVIRONMENT


logging.basicConfig(level=logging.INFO)


if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host='0.0.0.0',  # noqa: S104 - Compose Inngest reaches the host API.
        port=ENVIRONMENT.server_app_port,
        reload=True,
        proxy_headers=False,
    )
