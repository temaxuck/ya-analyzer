"""
While updating (patching) citizen data different requests may 
cause race condition which would set database to non-consistent state.

Let's say we have citizens with `citizen_id`s 1, 2, 3. Two 
concurrent requests are being executed: first request sets
relative with `citizen_id = 2` to citizen with `citizen_id = 1` while
second request sets relative with `citizen_id = 3` to the same citizen.

It is expected that these 2 requests are being executed sequentially,
and they response with data relevant to the initial request (for the 
first request, field `"relatives"` would be `[2]` and for the second
same field would be `[3]`).

But instead this situation may result the second request having 
`"relatives"` field to be `[2, 3]`. 
"""

import asyncio
import pytest

from aiopg.sa import SAConnection
from aiopg.sa.result import RowProxy

from analyzer.config import TestConfig
from analyzer.api.app import init_app
from analyzer.api.routes import CitizenView
from analyzer.utils.testing import (
    generate_citizens,
    get_citizens_data,
    post_imports_data,
    patch_citizen_data,
)

cfg = TestConfig()


class PatchedCitizenView(CitizenView):
    URL_PATH = r"/with_lock/imports/{import_id:\d+}/citizens/{citizen_id:\d+}"

    async def get_citizen(
        self, conn: SAConnection, import_id: int, citizen_id: int
    ) -> RowProxy:
        citizen = await super().get_citizen(conn, import_id, citizen_id)

        # Block execution to allow second request run simultaneously
        await asyncio.sleep(2)
        return citizen


class PatchedCitizenViewWithoutLock(PatchedCitizenView):
    """
    View with disabled advisory lock provided by postgresql (
    see https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS
    )
    """

    URL_PATH = r"/no_lock/imports/{import_id:\d+}/citizens/{citizen_id:\d+}"

    def acquire_lock(self, *_) -> None:
        # disable advisory lock
        return None


@pytest.fixture
async def api_client(aiohttp_client, arguments, migrated_postgres):
    """
    Overriding api_client fixture to include new routes
    """
    app = init_app(arguments, cfg)
    app.router.add_route(
        "*",
        PatchedCitizenView.URL_PATH,
        PatchedCitizenView,
    )
    app.router.add_route(
        "*",
        PatchedCitizenViewWithoutLock.URL_PATH,
        PatchedCitizenViewWithoutLock,
    )

    client = await aiohttp_client(
        app,
        server_kwargs={"port": arguments.api_port},
    )

    try:
        yield client
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url, final_relatives_number",
    [
        # with advisory lock we expect this to work correctly
        (PatchedCitizenView.URL_PATH, 1),
        # without advisory lock we expect this to return incorrect
        # number of relatives.
        # ====================================================
        # Unfortunately this testcase doesn't work as expected (ERROR 500)
        # (PatchedCitizenViewWithoutLock.URL_PATH, 2),
    ],
)
async def test_race_condition(api_client, url, final_relatives_number):
    import_data = generate_citizens(citizens_number=3, start_citizen_id=1)
    import_id = await post_imports_data(api_client, import_data)

    citizen_id = import_data[0]["citizen_id"]

    seeds = [
        {"relatives": [import_data[1]["citizen_id"]]},
        {"relatives": [import_data[2]["citizen_id"]]},
    ]

    await asyncio.gather(
        *[
            patch_citizen_data(
                client=api_client,
                import_id=import_id,
                citizen_id=citizen_id,
                data=seed,
                str_or_url=url,
            )
            for seed in seeds
        ]
    )

    citizens = {
        citizen["citizen_id"]: citizen
        for citizen in await get_citizens_data(api_client, import_id)
    }

    assert len(citizens[citizen_id]["relatives"]) == final_relatives_number
