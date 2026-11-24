"""Reconcile an Identity external-effect receipt from audited operator evidence.

Store the supporting evidence in the approved operations record first. This command
stores only its reference and SHA-256 digest. It requires direct database access and
is not exposed as an HTTP operation.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from typing import cast
from uuid import UUID

from shifu.identity.core.domain.structures import (
    AccountExternalEffectReceiptReconciliation,
    AccountExternalEffectReceiptResolution,
)
from shifu.identity.core.use_cases import (
    ListUnresolvedAccountExternalEffectReceiptsUseCase,
    ReconcileAccountExternalEffectReceiptUseCase,
)
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.shared.core.domain.errors import AppError
from shifu.shared.database.sqlalchemy import Session
from shifu.shared.providers.system_clock_provider import SystemClockProvider


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='List and reconcile Identity external-effect receipts.'
    )
    commands = parser.add_subparsers(dest='command', required=True)
    listing = commands.add_parser('list', help='List unresolved receipts.')
    listing.add_argument('--limit', type=int, default=100)

    reconcile = commands.add_parser('reconcile', help='Record audited evidence.')
    reconcile.add_argument('--account-id', required=True)
    reconcile.add_argument('--effect-id', required=True, type=UUID)
    reconcile.add_argument('--operation', required=True)
    reconcile.add_argument(
        '--resolution', required=True, choices=('applied', 'not_applied')
    )
    reconcile.add_argument('--operator-id', required=True)
    reconcile.add_argument('--evidence-reference', required=True)
    reconcile.add_argument('--evidence-sha256', required=True)
    reconcile.add_argument(
        '--confirm-no-live-operation',
        action='store_true',
        required=True,
        help='Confirm the remote operation is no longer running.',
    )
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    engine = Session.create_database_engine()
    try:
        database = SqlalchemyIdentityDatabase(engine)
        if arguments.command == 'list':
            receipts = ListUnresolvedAccountExternalEffectReceiptsUseCase(
                database
            ).execute(arguments.limit)
            for receipt in receipts:
                print(json.dumps(asdict(receipt), default=str, sort_keys=True))
        else:
            reconciliation = AccountExternalEffectReceiptReconciliation(
                account_id=arguments.account_id,
                effect_id=arguments.effect_id,
                operation=arguments.operation,
                resolution=cast(
                    'AccountExternalEffectReceiptResolution', arguments.resolution
                ),
                operator_id=arguments.operator_id,
                evidence_reference=arguments.evidence_reference,
                evidence_sha256=arguments.evidence_sha256,
                confirm_no_live_operation=arguments.confirm_no_live_operation,
            )
            ReconcileAccountExternalEffectReceiptUseCase(
                database, SystemClockProvider()
            ).execute(reconciliation)
            print(
                json.dumps(
                    {
                        'effect_id': str(reconciliation.effect_id),
                        'operation': reconciliation.operation,
                        'resolution': reconciliation.resolution,
                        'recorded': True,
                    },
                    sort_keys=True,
                )
            )
    except AppError as error:
        print(f'Reconciliation rejected: {error.message}')
        return 2
    except ValueError:
        print('Reconciliation rejected: invalid command input.')
        return 2
    else:
        return 0
    finally:
        engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
