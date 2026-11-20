\set ON_ERROR_STOP on

CREATE SCHEMA IF NOT EXISTS rds_lab;

CREATE TABLE IF NOT EXISTS rds_lab.identity_accounts (
    id varchar(26) PRIMARY KEY,
    display_name varchar(160) NOT NULL,
    email varchar(320) NOT NULL,
    password_hash varchar(255) NOT NULL,
    status varchar(40) NOT NULL,
    access_version integer NOT NULL,
    time_zone varchar(64),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    confirmed_at timestamptz,
    deleted_at timestamptz,
    deletion_reason varchar(64),
    retained_session_id text,
    retained_session_access_version integer,
    CONSTRAINT ck_identity_accounts_retained_session CHECK (
        (retained_session_id IS NULL AND retained_session_access_version IS NULL) OR
        (retained_session_id IS NOT NULL AND retained_session_id <> '' AND
         retained_session_access_version IS NOT NULL AND
         retained_session_access_version > 0 AND
         retained_session_access_version < access_version)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_identity_accounts_active_email
    ON rds_lab.identity_accounts (email)
    WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS rds_lab.learning_goals (
    id varchar(26) PRIMARY KEY,
    account_id varchar(26) NOT NULL,
    title varchar(240) NOT NULL,
    description varchar(4000) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_learning_goal_account_id
    ON rds_lab.learning_goals (account_id);

CREATE TABLE IF NOT EXISTS rds_lab.gamification_xp_grants (
    id varchar(26) PRIMARY KEY,
    account_id varchar(26) NOT NULL,
    fact_id varchar(26) NOT NULL,
    amount integer NOT NULL,
    origin json NOT NULL,
    occurred_at timestamptz NOT NULL,
    granted_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_gamification_xp_grant_account_id
    ON rds_lab.gamification_xp_grants (account_id);
