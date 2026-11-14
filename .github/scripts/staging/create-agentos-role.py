"""Create or update the AgentOS runtime database role inside the VPC.

Run it in the server container through run-server-task.sh. The container already
has the server secrets in its environment:

- DATABASE_URL logs in as the database admin, who is allowed to create roles.
- AGENTOS_DATABASE_URL holds the role name and its password.

This does what apps/server/scripts/create_agentos_runtime_role.sql does, without
psql, so it is safe to run again. It prints no secret value. Finally it logs in as
the role to prove that AGENTOS_DATABASE_URL works.
"""

import os
import sys
from urllib.parse import unquote, urlsplit

import psycopg
from psycopg import sql


def read_url(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f'{name} is not set.')
    # SQLAlchemy URLs carry the driver name, which psycopg does not accept.
    return value.replace('postgresql+psycopg://', 'postgresql://', 1)


admin_url = read_url('DATABASE_URL')
runtime_url = read_url('AGENTOS_DATABASE_URL')

runtime = urlsplit(runtime_url)
role_name = unquote(runtime.username or '')
role_password = unquote(runtime.password or '')
if not role_name or not role_password:
    sys.exit('AGENTOS_DATABASE_URL must contain a role name and a password.')

with psycopg.connect(admin_url, autocommit=True) as connection:
    database_name = connection.execute('SELECT current_database()').fetchone()[0]
    exists = connection.execute(
        'SELECT 1 FROM pg_roles WHERE rolname = %s', (role_name,)
    ).fetchone()

    attributes = sql.SQL('LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT')
    verb = sql.SQL('ALTER') if exists else sql.SQL('CREATE')
    connection.execute(
        sql.SQL('{} ROLE {} {} PASSWORD {}').format(
            verb,
            sql.Identifier(role_name),
            attributes,
            sql.Literal(role_password),
        )
    )
    connection.execute(
        sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(
            sql.Identifier(database_name), sql.Identifier(role_name)
        )
    )
    print(f'Role {role_name} {"updated" if exists else "created"} in {database_name}.')

with psycopg.connect(runtime_url) as connection:
    current_user = connection.execute('SELECT current_user').fetchone()[0]
    print(f'Logged in as {current_user} with AGENTOS_DATABASE_URL.')
