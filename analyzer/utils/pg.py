import logging

from aiohttp import web
from asyncpgsa import PG
from configargparse import Namespace

logger = logging.getLogger(__name__)

CENSORED = "***"
MAX_QUERY_ARGS = 32767


async def setup_pg(app: web.Application, args: Namespace):
    db_info = args.pg_url.with_password(CENSORED)
    logger.info(f"Connecting to database: {db_info}")

    app["pg"] = PG()
    await app["pg"].init(
        str(args.pg_url),
        min_size=args.pg_pool_min_size,
        max_size=args.pg_pool_max_size,
    )
    await app["pg"].fetchval("SELECT 1")
    logger.info(f"Connected to database: {db_info}")

    try:
        yield
    finally:
        logger.info(f"Disconnecting from database: {db_info}")
        await app["pg"].pool.close()
        logger.info(f"Disconnected from database: {db_info}")
