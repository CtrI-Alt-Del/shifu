from typing import cast

from inngest import Function, Inngest

from shifu.identity.messaging.inngest.jobs import LogMainPageEnteredJob


class IdentityInngestMessaging:
    """Declare the Inngest functions owned by Identity."""

    @staticmethod
    def register_jobs(inngest: Inngest) -> list[Function[object]]:
        return [
            cast('Function[object]', LogMainPageEnteredJob.handle(inngest)),
        ]
