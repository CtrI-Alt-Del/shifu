"""Local-only demonstration: request the streak reminder for one account now.

The command skips only the reminder-hour check. Every other eligibility rule and the
normal delivery path (outbox, Inngest, Communication) stay unchanged, so the API and
Inngest must be running for a notification to arrive.

Before requesting, it clears the account's reminder for the current local day,
whatever its status, so every run can deliver again. Only this local command does it.

The mode guard runs before any application setting is loaded, so a non-local run
refuses with a short message instead of a configuration error.
"""

import os
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

SLOT_MINUTES = 15
USAGE = 'Usage: uv run poe reminders:send-now <email>'


def floor_to_slot(moment: datetime) -> datetime:
    floored = moment.astimezone(UTC).replace(second=0, microsecond=0)
    return floored - timedelta(minutes=floored.minute % SLOT_MINUTES)


def run(
    arguments: Sequence[str],
    *,
    server_app_mode: str,
    now: datetime | None = None,
) -> int:
    if server_app_mode != 'local':
        print(
            'This command only runs when SHIFU_SERVER_APP_MODE is local.',
            file=sys.stderr,
        )
        return 2

    if len(arguments) != 1:
        print(USAGE, file=sys.stderr)
        return 2

    from shifu.communication.core.use_cases import ClearCurrentStreakRemindersUseCase
    from shifu.communication.database.sqlalchemy import SqlalchemyCommunicationDatabase
    from shifu.gamification.core.use_cases import RequestStreakReminderUseCase
    from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
    from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
    from shifu.identity.providers.identity_active_account_provider import (
        IdentityActiveAccountProvider,
    )
    from shifu.shared.core.domain.errors import ValidationError
    from shifu.shared.core.domain.structures import EmailAddress
    from shifu.shared.database.sqlalchemy.session import Session
    from shifu.shared.providers.system_clock_provider import SystemClockProvider

    try:
        email = EmailAddress.create(arguments[0]).value
    except ValidationError:
        print('Enter a valid e-mail address.', file=sys.stderr)
        return 2

    engine = Session.create_database_engine()
    try:
        identity_database = SqlalchemyIdentityDatabase(engine=engine)
        with identity_database.transaction() as repositories:
            account = repositories.accounts.find_non_deleted_by_email(email)
        if account is None:
            print('No account was found for that e-mail address.', file=sys.stderr)
            return 1

        cleared = ClearCurrentStreakRemindersUseCase(
            SqlalchemyCommunicationDatabase(engine=engine),
            SystemClockProvider(),
        ).execute(account.id)

        requested = RequestStreakReminderUseCase(
            SqlalchemyGamificationDatabase(engine=engine),
            IdentityActiveAccountProvider(identity_database),
        ).execute(
            account.id,
            slot_start=floor_to_slot(now or datetime.now(UTC)),
            ignore_hour=True,
        )
    finally:
        engine.dispose()

    if cleared:
        print("Cleared today's earlier reminder so it can be requested again.")
    if requested:
        print('Streak reminder requested. It is delivered through Inngest shortly.')
    else:
        print('Nothing was requested: the account is not eligible for a reminder.')
    return 0


def main() -> None:
    sys.exit(
        run(
            sys.argv[1:],
            server_app_mode=os.environ.get('SHIFU_SERVER_APP_MODE', 'local'),
        )
    )


if __name__ == '__main__':
    main()
