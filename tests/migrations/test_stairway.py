import pytest

from alembic.config import Config
from alembic.command import upgrade, downgrade
from alembic.script import ScriptDirectory, Script
from types import SimpleNamespace


from analyzer.utils.pg import make_alembic_config


def get_revesions():
    options = SimpleNamespace(
        config="alembic.ini",
        pg_url=None,
        name="alembic",
        raiseerr=False,
        x=None,
    )
    alembic_config = make_alembic_config(options)

    # migrations directory
    revisions_dir = ScriptDirectory.from_config(alembic_config)

    revisions = list(revisions_dir.walk_revisions("base", "heads"))
    revisions.reverse()

    return revisions


@pytest.mark.parametrize("revision", get_revesions())
def test_migrations_stairway(alembic_config: Config, revision: Script):
    upgrade(alembic_config, revision.revision)
    downgrade(alembic_config, revision.down_revision or "base")
    upgrade(alembic_config, revision.revision)
