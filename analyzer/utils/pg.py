import logging
import os

from aiohttp import web
from aiopg.sa import create_engine, SAConnection
from alembic.config import Config as AlembicConfig
from typing import AsyncIterable
from configargparse import Namespace
from pathlib import Path
from sqlalchemy.sql import Select
from sqlalchemy.sql.functions import Function
from sqlalchemy import Column, Numeric, cast, func
from typing import Union
from types import SimpleNamespace

logger = logging.getLogger(__name__)

CENSORED = "*****"
MAX_QUERY_ARGS = 32767
PROJECT_PATH = Path(__file__).parent.parent.resolve()


def rounded(column: Column, fraction: int = 2) -> Function:
    return func.round(cast(column, Numeric), fraction)


async def setup_pg(app: web.Application, args: Namespace):
    db_info = args.pg_url.with_password(CENSORED)
    logger.info(f"Connecting to database: {db_info}")

    engine = await create_engine(
        dbname=args.pg_url.name,
        user=args.pg_url.user,
        password=args.pg_url.password,
        host=args.pg_url.host,
        port=args.pg_url.port,
        minsize=args.pg_pool_min_size,
        maxsize=args.pg_pool_max_size,
    )
    app["pg"] = engine

    async with engine.acquire() as conn:
        await conn.execute("SELECT 1")
        logger.info(f"Connected to database: {db_info}")
        datestyle = "GERMAN, DMY"  # TODO: unhardcode to something like app["cfg"].PG_DATE_FORMAT
        await conn.execute(f"SET datestyle = '{datestyle}'")
        logger.info(f"Database date style set to: {datestyle}")

    try:
        yield
    finally:
        logger.info(f"Disconnecting from database: {db_info}")
        engine.close()
        await engine.wait_closed()
        logger.info(f"Disconnected from database: {db_info}")


def make_alembic_config(
    cmd_opts: Union[SimpleNamespace, Namespace],
    base_path: str = PROJECT_PATH,
) -> AlembicConfig:
    """
    Create alembic config object based on the cmd arguments
    Substitute relative paths to absolute
    """

    if not os.path.isabs(cmd_opts.config):
        cmd_opts.config = os.path.join(base_path, cmd_opts.config)

    config = AlembicConfig(
        file_=cmd_opts.config,
        ini_section=cmd_opts.name,
        cmd_opts=cmd_opts,
    )

    alembic_location = config.get_main_option("script_location")
    if not os.path.isabs(alembic_location):
        config.set_main_option(
            "script_location", os.path.join(base_path, alembic_location)
        )

    if cmd_opts.pg_url:
        config.set_main_option("sqlalchemy.url", cmd_opts.pg_url)

    return config


class SelectQuery(AsyncIterable):
    """
    Used to send data from PostgreSQL straight to the client
    after recieving it, in parts, without buffering all data
    """

    PREFETCH = 500

    __slots__ = ("query", "conn", "prefetch", "timeout_ms")

    def __init__(
        self,
        query: Select,
        conn: SAConnection,
        prefetch: int = None,
        timeout_ms: int = None,
    ):
        self.query = query
        self.conn = conn
        self.prefetch = prefetch or self.PREFETCH
        self.timeout_ms = timeout_ms

    async def __aiter__(self):
        async with self.conn.begin() as _:
            if self.timeout_ms is not None:
                await self.conn.execute(f"SET statement_timeout = {self.timeout_ms}")
            async with self.conn.execute(self.query) as cur:
                while True:
                    rows = await cur.fetchmany(self.prefetch)
                    if not rows:
                        break
                    for row in rows:
                        yield row
