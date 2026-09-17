"""Application-owned Inngest client and function registration."""

from collections.abc import Callable, Sequence
from typing import cast

from fastapi import FastAPI
from inngest import Function, Inngest
from inngest.fast_api import serve

from shifu.shared.messaging.inngest.inngest_client import InngestClient


JobGroupRegistrar = Callable[[Inngest], list[Function[object]]]


class InngestMessaging:
    """Compose one Inngest client and register module-owned job groups."""

    @staticmethod
    def register(
        app: FastAPI,
        job_group_registrars: Sequence[JobGroupRegistrar] = (),
    ) -> Inngest:
        inngest = cast('Inngest', InngestClient.create())

        serve(
            app,
            client=inngest,
            functions=[
                function
                for registrar in job_group_registrars
                for function in registrar(inngest)
            ],
        )

        return inngest
