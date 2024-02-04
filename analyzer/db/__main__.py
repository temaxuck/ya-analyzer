import os
from alembic.config import CommandLine, Config
from analyzer.config import Config as analyzer_cfg
from pathlib import Path

PROJECT_PATH = Path(__file__).parent.parent.resolve()


def main():
    alembic = CommandLine()
    alembic.parser.add_argument(
        "--pg-url",
        default=os.getenv("ANALYZER_PG_URL", analyzer_cfg.DATABASE_URI),
        help="PostgreSQL URL [env var: ANALYZER_PG_URL]",
    )

    options = alembic.parser.parse_args()

    if not os.path.isabs(options.config):
        options.config = os.path.join(PROJECT_PATH, options.config)

    config = Config(file_=options.config, ini_section=options.name, cmd_opts=options)

    alembic_location = config.get_main_option("script_location")
    if not os.path.isabs(alembic_location):
        config.set_main_option(
            "script_location", os.path.join(PROJECT_PATH, alembic_location)
        )

    config.set_main_option("sqlalchemy.url", options.pg_url)

    exit(alembic.run_cmd(config, options))


if __name__ == "__main__":
    main()
