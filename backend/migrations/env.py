import os
from logging.config import fileConfig

from dotenv import load_dotenv
import sqlalchemy as sa
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from backend import models

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    # disable_existing_loggers=False: si no, correr migraciones desde dentro del proceso (las
    # pruebas) silencia los loggers de la app (p. ej. el de auditoría).
    fileConfig(config.config_file_name, disable_existing_loggers=False)

load_dotenv()
# "%" se duplica porque ConfigParser lo interpreta (una contraseña con "%" rompería la URL).
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL").replace("%", "%%"))

# add your model's MetaData object here for 'autogenerate' support
target_metadata = models.Base.metadata

# Tablas que existen en la base pero NO son modelos de SQLAlchemy (SQL crudo, ver migración 0002):
# sin esto `alembic check` y --autogenerate proponen borrarlas.
TABLAS_FUERA_DE_LOS_MODELOS = {"knowledge_base"}


def compare_type(context, inspected_column, metadata_column, inspected_type, metadata_type):
    """TEXT y VARCHAR sin largo son lo mismo en Postgres: no se reportan como cambio de tipo
    (devolver None deja la comparación normal para todo lo demás)."""
    sin_largo = lambda t: isinstance(t, (sa.Text, sa.String)) and getattr(t, "length", None) is None
    if sin_largo(inspected_type) and sin_largo(metadata_type):
        return False
    return None


def include_object(obj, name, type_, reflected, compare_to):
    return not (type_ == "table" and reflected and name in TABLAS_FUERA_DE_LOS_MODELOS)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
        compare_type=compare_type,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            include_object=include_object, compare_type=compare_type,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
