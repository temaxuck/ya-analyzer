import pytest

from http import HTTPStatus
from random import randint
from typing import Tuple, Mapping, Any, List

from analyzer.utils.testing import (
    CitizenType,
    generate_citizen,
    generate_citizens,
    post_imports_data,
    get_citizen_presents_data,
)

PresentsByMonthType = Mapping[str, Any]
TestCaseType = Tuple[List[CitizenType], PresentsByMonthType]


def make_presents_by_month_response(values: Mapping[str, Any] = None):
    if values:
        return {str(month): values.get(str(month), []) for month in range(1, 13)}

    return {str(month): [] for month in range(1, 13)}


CASES: List[TestCaseType] = [
    # A citizen has two relatives in one month
    # Two citizens have one relative in one month
    (
        [
            generate_citizen(citizen_id=1, birth_date="31.12.2020", relatives=[2, 3]),
            generate_citizen(citizen_id=2, birth_date="17.04.2020", relatives=[1]),
            generate_citizen(citizen_id=3, birth_date="01.04.2020", relatives=[1]),
        ],
        make_presents_by_month_response(
            {
                "4": [
                    {"citizen_id": 1, "presents": 2},
                ],
                "12": [
                    {"citizen_id": 2, "presents": 1},
                    {"citizen_id": 3, "presents": 1},
                ],
            }
        ),
    ),
    # A citizen has no relatives
    (
        [
            generate_citizen(relatives=[]),
        ],
        make_presents_by_month_response(),
    ),
    # Empty import_data
    (
        [],
        make_presents_by_month_response(),
    ),
    # A citizen is a relative to themselves
    # Expect them to buy present for themselves
    (
        [generate_citizen(citizen_id=1, birth_date="15.09.2009", relatives=[1])],
        make_presents_by_month_response(
            {
                "9": [
                    {"citizen_id": 1, "presents": 1},
                ]
            }
        ),
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("import_data, expected_presents", CASES)
async def test_get_citizens_presents(api_client, import_data, expected_presents):
    # Generate one more import record to make sure handler
    # distincts citizens from different import records
    await post_imports_data(api_client, generate_citizens(citizens_number=3))

    import_id = await post_imports_data(api_client, import_data)
    actual_presents = await get_citizen_presents_data(api_client, import_id)

    assert expected_presents == actual_presents


@pytest.mark.asyncio
async def test_get_citizens_presents_nonexistent(api_client):
    await get_citizen_presents_data(
        api_client, randint(1, 1000), expected_status=HTTPStatus.NOT_FOUND
    )
