# alembic/env.py
from __future__ import annotations
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.core.config import settings
from app.core.db import Base
from app.models import *  # <-- importa TODO para poblar Base.metadata

target_metadata = Base.metadata

def _run_migrations(connection) -> None:
    """Bloque sincrónico que ejecuta las migraciones dentro de una transacción."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_offline() -> None:
    # Alembic offline no usa driver async (quitamos +aiomysql)
    url = settings.async_database_url.replace("+aiomysql", "")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        {"sqlalchemy.url": settings.async_database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Ejecutamos la función sincrónica en el hilo del engine
        await connection.run_sync(_run_migrations)

def run() -> None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        import asyncio
        asyncio.run(run_migrations_online())

run()
