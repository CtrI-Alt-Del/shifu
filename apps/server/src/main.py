import uvicorn

from shifu.app import app as app
from shifu.shared.constants import ENVIRONMENT


if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host='127.0.0.1',
        port=ENVIRONMENT.server_app_port,
        reload=True,
    )
