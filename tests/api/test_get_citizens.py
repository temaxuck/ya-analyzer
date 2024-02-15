import pytest

from datetime import datetime
from http import HTTPStatus
from typing import List
from sqlalchemy.engine import Connection


from analyzer.config import TestConfig
from analyzer.db.schema import import_table, citizen_table, relation_table
from analyzer.utils.testing import (
    get_citizens_data,
    generate_citizen,
    CitizenType,
    compare_citizen_groups,
)

cfg = TestConfig()

datasets = [
    # A citizen with several relatives
    # Test standard expected behaviour
    [
        generate_citizen(citizen_id=1, relatives=[2, 3]),
        generate_citizen(citizen_id=2, relatives=[1]),
        generate_citizen(citizen_id=3, relatives=[1]),
    ],
    # A citizen without relatives
    # Field `relatives` should contain an empty list
    # (not list of None values, which may be caused by `LEFT JOIN`)
    [
        generate_citizen(citizen_id=1, relatives=[]),
    ],
    # A citizen who's relative to himself
    # (I guess the author meant this situation
    # to be an example when a citizen buys presents for himself)
    # Handler (Route) should return citizen's id within
    # the list of citizens
    [
        generate_citizen(
            citizen_id=1,
            name="John",
            gender="male",
            birth_date="17.02.2020",
            relatives=[1],
        ),
    ],
    # Empty data
    [],
]


def import_dataset(connection: Connection, citizens: List[CitizenType]) -> int:
    query = import_table.insert().returning(import_table.c.import_id)
    import_id = connection.execute(query).scalar()

    citizen_rows = []
    relations_rows = []

    for citizen in citizens:
        citizen_rows.append(
            {
                "import_id": import_id,
                "citizen_id": citizen["citizen_id"],
                "name": citizen["name"],
                "birth_date": datetime.strptime(
                    citizen["birth_date"], cfg.BIRTH_DATE_FORMAT
                ).date(),
                "gender": citizen["gender"],
                "town": citizen["town"],
                "street": citizen["street"],
                "building": citizen["building"],
                "apartment": citizen["apartment"],
            }
        )

        for relative_id in citizen["relatives"]:
            relations_rows.append(
                {
                    "import_id": import_id,
                    "citizen_id": citizen["citizen_id"],
                    "relative_id": relative_id,
                }
            )

    if citizen_rows:
        query = citizen_table.insert().values(citizen_rows)
        connection.execute(query)

    if relations_rows:
        query = relation_table.insert().values(relations_rows)
        connection.execute(query)

    return import_id


@pytest.mark.asyncio
@pytest.mark.parametrize("dataset", datasets)
async def test_get_citizens(api_client, migrated_postgres_connection, dataset):
    # Before running each test create a new import record in database
    # with one citizen to make sure handler distinguishes citizens of different imports
    import_dataset(migrated_postgres_connection, [generate_citizen()])

    import_id = import_dataset(migrated_postgres_connection, dataset)
    actual_citizens = await get_citizens_data(api_client, import_id)
    assert compare_citizen_groups(actual_citizens, dataset)


@pytest.mark.asyncio
async def test_get_non_existing_import(api_client):
    await get_citizens_data(api_client, 999, HTTPStatus.NOT_FOUND)
