import pytest
import pytz

from copy import copy
from datetime import datetime, timedelta
from http import HTTPStatus
from numbers import Number
from typing import Union, Tuple, Mapping, List
from random import randint
from unittest.mock import patch

from analyzer.config import TestConfig
from analyzer.utils.testing import (
    CitizenType,
    generate_citizen,
    post_imports_data,
    get_age_stats_data,
)

cfg = TestConfig()

# Fixed datetime object which is needed to fix citizens' age
CURRENT_DATE = datetime(2024, 2, 13, tzinfo=pytz.utc)


def age2date(years: int, days: int = 0, base_date: datetime = CURRENT_DATE) -> str:
    """Get date (string) from age in years and days(optional)

    Args:
        years (int): number of years.
        days (int, optional): number of days since the last birthday. Defaults to 0.
        base_date (datetime, optional): base datetime object which would be considered \
            to be `today()` for the test application instance. Defaults to CURRENT_DATE.

    Returns:
        str: birth date in format specified in `analyzer.TestConfig.BIRTH_DATE_FORMAT`
    """
    birth_date = copy(base_date).replace(year=base_date.year - years)
    birth_date -= timedelta(days=days)

    return birth_date.strftime(cfg.BIRTH_DATE_FORMAT)


AgePercentileByTownType = List[Mapping[str, Union[str, Number]]]
TestCaseType = Tuple[List[CitizenType], AgePercentileByTownType]

CASES: List[TestCaseType] = [
    # 3 citizens having their birthday tommorow
    # Test if the handler correctly calculates
    # percentiles only using whole years
    (
        [
            generate_citizen(
                citizen_id=1,
                town="Moscow",
                birth_date=age2date(years=10, days=364),
            ),
            generate_citizen(
                citizen_id=2,
                town="Moscow",
                birth_date=age2date(years=30, days=364),
            ),
            generate_citizen(
                citizen_id=3,
                town="Moscow",
                birth_date=age2date(years=50, days=364),
            ),
        ],
        [
            {
                "town": "Moscow",
                "p50": 30.0,
                "p75": 40.0,
                "p99": 49.6,
            }
        ],
    ),
    # A citizen having a birthday today
    # Test if the handler correctly calculates
    # percentiles for citizens who has birthday today
    (
        [
            generate_citizen(
                town="Moscow",
                birth_date=age2date(years=10),
            ),
        ],
        [
            {
                "town": "Moscow",
                "p50": 10.0,
                "p75": 10.0,
                "p99": 10.0,
            }
        ],
    ),
    # Empty import_data
    # Test if handler is not failing it
    (
        [],
        [],
    ),
]


@patch("analyzer.api.routes.AgeStatsView.CURRENT_DATE", new=CURRENT_DATE)
@pytest.mark.asyncio
@pytest.mark.parametrize("citizens, expected_agestats", CASES)
async def test_get_age_stats(api_client, citizens, expected_agestats):
    # Generate one more import record to make sure handler
    # distincts citizens from different import records
    await post_imports_data(api_client, [generate_citizen(town="Osaka")])

    import_id = await post_imports_data(api_client, citizens)
    actual_agestats = await get_age_stats_data(api_client, import_id)

    assert len(expected_agestats) == len(
        actual_agestats
    ), "Number of towns is different"

    actual_towns_map = {group["town"]: group for group in actual_agestats}

    for group in expected_agestats:
        assert group["town"] in actual_towns_map
        actual_group = actual_towns_map[group["town"]]

        for percentile in ["p50", "p75", "p99"]:
            assert group[percentile] == actual_group[percentile], (
                f"{group['town']} {percentile} {actual_group[percentile]} does "
                f"not match expected value {group[percentile]}"
            )


@pytest.mark.asyncio
async def test_get_age_stats_nonexistent(api_client):
    await get_age_stats_data(
        api_client,
        randint(1, 1000),
        HTTPStatus.NOT_FOUND,
    )
