from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from shifu.communication.database.sqlalchemy import models as communication_models
from shifu.curriculum.database.sqlalchemy import models as curriculum_models
from shifu.identity.database.sqlalchemy import models as identity_models
from shifu.learning.database.sqlalchemy import models as learning_models
from shifu.shared.database.sqlalchemy.base import Base
from shifu.shared.database.sqlalchemy.settings import DatabaseSettings


_MODEL_MODULES = (
    communication_models,
    curriculum_models,
    identity_models,
    learning_models,
)


if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DatabaseSettings.from_environment().url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = context.config.get_section(context.config.config_ini_section, {})
    configuration['sqlalchemy.url'] = DatabaseSettings.from_environment().url
    connectable = engine_from_config(
        configuration,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
