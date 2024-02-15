import os
import pytest
import uuid

from alembic.command import upgrade
from sqlalchemy import create_engine
from sqlalchemy_utils import create_database, drop_database
from types import SimpleNamespace
from yarl import URL


from analyzer.api.app import init_app
from analyzer.config import TestConfig
from analyzer.utils.argparse import get_arg_parser
from analyzer.utils.pg import make_alembic_config

cfg = TestConfig()

PG_URL = os.getenv("CI_ANALYZER_PG_URL", cfg.DATABASE_URI)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def postgres():
    """
    Create temporary postgresql instance for testing
    """

    tmp_name = ".".join([uuid.uuid4().hex, "pytest"])
    tmp_url = str(URL(PG_URL).with_path(tmp_name))

    create_database(tmp_url)

    try:
        yield tmp_url
    finally:
        drop_database(tmp_url)


@pytest.fixture
def alembic_config(postgres):
    """
    Create object with alembic configuration for the temporary database

    Yields postgres connection string
    """

    cmd_options = SimpleNamespace(
        config="alembic.ini",
        name="alembic",
        pg_url=postgres,
        raiseerr=False,
        x=None,
    )

    return make_alembic_config(cmd_options)


# API fixtures


@pytest.fixture
def migrated_postgres(alembic_config, postgres):
    """
    Return URL to migrated database
    """
    upgrade(alembic_config, "head")
    return postgres


@pytest.fixture
def arguments(unused_tcp_port_factory, migrated_postgres):
    """
    Get arguments for app initialization
    """

    parser = get_arg_parser(cfg)

    return parser.parse_args(
        [
            "--log-level=debug",
            "--api-host=127.0.0.1",
            f"--api-port={unused_tcp_port_factory()}",
            f"--pg-url={migrated_postgres}",
        ]
    )


@pytest.fixture
async def api_client(aiohttp_client, arguments):
    app = init_app(arguments, cfg)

    client = await aiohttp_client(app, server_kwargs={"port": arguments.api_port})

    try:
        yield client
    finally:
        await client.close()


@pytest.fixture
def migrated_postgres_connection(migrated_postgres):
    """
    Synchronous connection with migrated postgres database
    """

    engine = create_engine(migrated_postgres)
    conn = engine.connect()

    try:
        yield conn
    finally:
        conn.close()
        engine.dispose()
