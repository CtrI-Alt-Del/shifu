from collections.abc import Callable, Iterable
from threading import Event as ThreadEvent
from threading import Thread
from typing import Protocol

import psycopg


EVENTS_CHANNEL = 'shifu_events'


class _PostgresNotification(Protocol):
    payload: str


class PostgresListenerConnection(Protocol):
    def execute(self, query: str) -> object: ...

    def commit(self) -> object: ...

    def notifies(self) -> Iterable[_PostgresNotification]: ...

    def close(self) -> object: ...


class SqlalchemyEventsRepositoryListener:
    def __init__(
        self,
        connection: PostgresListenerConnection,
        on_event: Callable[[str], None],
    ) -> None:
        self._connection: PostgresListenerConnection = connection
        self._on_event: Callable[[str], None] = on_event
        self._stopped = ThreadEvent()
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            self._connection.execute(f'LISTEN {EVENTS_CHANNEL}')
            self._connection.commit()
            for notification in self._connection.notifies():
                if self._stopped.is_set():
                    break
                self._on_event(notification.payload)
        except (OSError, psycopg.Error):
            if not self._stopped.is_set():
                return

    def unlisten(self) -> None:
        if self._stopped.is_set():
            return
        self._stopped.set()
        try:
            self._connection.close()
        finally:
            self._thread.join(timeout=1)
