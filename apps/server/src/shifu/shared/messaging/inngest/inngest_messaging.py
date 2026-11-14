"""Application-owned Inngest client and function registration."""

from inngest._internal.client_lib.client import Inngest


from collections.abc import Callable, Sequence
from typing import cast

from fastapi import FastAPI
from inngest import Function
from inngest.fast_api import serve

from shifu.shared.messaging.inngest.inngest_client import InngestClient
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider


JobGroupRegistrar = Callable[[Inngest, TelemetryProvider], list[Function[object]]]


class InngestMessaging:
    """Compose one Inngest client and register module-owned job groups."""

    @staticmethod
    def register(
        app: FastAPI,
        telemetry_provider: TelemetryProvider,
        job_group_registrars: Sequence[JobGroupRegistrar] = (),
    ) -> Inngest:
        inngest: Inngest = cast('Inngest', InngestClient.create())

        serve(
            app,
            client=inngest,
            functions=[
                function
                for registrar in job_group_registrars
                for function in registrar(inngest, telemetry_provider)
            ],
        )

        return inngest
