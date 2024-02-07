import logging

from aiopg.sa import create_engine

from aiohttp import web
from configargparse import Namespace

logger = logging.getLogger(__name__)

CENSORED = "*****"
MAX_QUERY_ARGS = 32767


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
