import pytest

from datetime import date, timedelta
from typing import Tuple, List

from http import HTTPStatus


from analyzer.config import TestConfig
from analyzer.utils.testing import (
    MAX_INTEGER,
    CitizenType,
    compare_citizen_groups,
    generate_citizen,
    generate_citizens,
    post_imports_data,
    get_citizens_data,
)

cfg = TestConfig()

TestCaseType = Tuple[List[CitizenType], HTTPStatus]


LONGEST_STR = "Ё" * 256
CASES: Tuple[TestCaseType, ...] = (
    # ==== POSITIVE TESTCASES ====
    # Post a simple citizen with no relatives
    # Handler is expected to create one import record with one citizen
    (
        [
            generate_citizen(relatives=[]),
        ],
        HTTPStatus.CREATED,
    ),
    # Post a citizen with several relatives
    # Handler is expected to create one import record with 3 relative citizens
    (
        [
            generate_citizen(citizen_id=1, relatives=[2, 3]),
            generate_citizen(citizen_id=2, relatives=[1]),
            generate_citizen(citizen_id=3, relatives=[1]),
        ],
        HTTPStatus.CREATED,
    ),
    # Post a citizen who is considered to be relative to themselves
    # Handler is expected to create one import record with 1 citizen relative to themselves
    (
        [
            generate_citizen(
                citizen_id=1,
                name="Jake",
                gender="male",
                birth_date="15.01.1971",
                town="Amsterdam",
                relatives=[1],
            ),
        ],
        HTTPStatus.CREATED,
    ),
    # Post large import record with large values
    # Handler is expected to not fall and create the import record
    (
        generate_citizens(
            citizens_number=10000,
            relations_number=1000,
            start_citizen_id=MAX_INTEGER - 10000,
            gender="female",
            name=LONGEST_STR,
            town=LONGEST_STR,
            street=LONGEST_STR,
            building=LONGEST_STR,
            apartment=MAX_INTEGER,
        ),
        HTTPStatus.CREATED,
    ),
    # Post an empty import record
    # Handler is expected to not fall and create the import record
    (
        [],
        HTTPStatus.CREATED,
    ),
    # Post a citizen with birth date to be today()
    # Handler is expected to not fall and create the import record
    (
        [
            generate_citizen(
                birth_date=date.today().strftime(cfg.BIRTH_DATE_FORMAT),
            )
        ],
        HTTPStatus.CREATED,
    ),
    # ==== NEGATIVE TESTCASES ====
    # Post a citizen with birth date to be future
    # Handler is expected to not fall and response with BAD_REQUEST status
    (
        [
            generate_citizen(
                birth_date=(date.today() + timedelta(days=1)).strftime(
                    cfg.BIRTH_DATE_FORMAT
                ),
            )
        ],
        HTTPStatus.BAD_REQUEST,
    ),
    # Post 2 citizens with same id
    # Handler is expected to not fall and response with BAD_REQUEST status
    (
        [
            generate_citizen(citizen_id=1),
            generate_citizen(citizen_id=1),
        ],
        HTTPStatus.BAD_REQUEST,
    ),
    # Post 2 citizens except one of them is not relative to another
    # Handler is expected to not fall and response with BAD_REQUEST status
    (
        [
            generate_citizen(citizen_id=1, relatives=[2]),
            generate_citizen(citizen_id=2, relatives=[]),
        ],
        HTTPStatus.BAD_REQUEST,
    ),
    # Post a citizen with a non-existing relative
    # Handler is expected to not fall and response with BAD_REQUEST status
    (
        [
            generate_citizen(citizen_id=1, relatives=[2]),
        ],
        HTTPStatus.BAD_REQUEST,
    ),
    # Post 2 citizens with non-unique relatives
    # Handler is expected to not fall and response with BAD_REQUEST status
    (
        [
            generate_citizen(citizen_id=1, relatives=[2]),
            generate_citizen(citizen_id=2, relatives=[1, 1]),
        ],
        HTTPStatus.BAD_REQUEST,
    ),
)


@pytest.mark.asyncio
@pytest.mark.parametrize("citizens, expected_status", CASES)
async def test_post_imports(api_client, citizens, expected_status):
    import_id = await post_imports_data(api_client, citizens, expected_status)

    if expected_status == HTTPStatus.CREATED:
        imported_citizens = await get_citizens_data(api_client, import_id)
        assert compare_citizen_groups(imported_citizens, citizens)
