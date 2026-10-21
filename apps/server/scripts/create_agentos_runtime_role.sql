\set ON_ERROR_STOP on

SELECT format(
    'CREATE ROLE shifu_agentos_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD %L',
    :'runtime_password'
)
WHERE NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'shifu_agentos_runtime'
)
\gexec

ALTER ROLE shifu_agentos_runtime
    LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT
    PASSWORD :'runtime_password';

GRANT CONNECT ON DATABASE :"database_name" TO shifu_agentos_runtime;
