import os

import uvicorn

from shifu.app import app as app


if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host='127.0.0.1',
        port=int(os.getenv('SHIFU_SERVER_APP_PORT', '9000')),
        reload=True,
    )
