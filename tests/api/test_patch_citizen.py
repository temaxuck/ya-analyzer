import pytest

from datetime import date, timedelta
from http import HTTPStatus
from random import randint

from analyzer.config import TestConfig
from analyzer.utils.testing import (
    compare_citizens,
    compare_citizen_groups,
    generate_citizen,
    generate_citizens,
    get_citizens_data,
    post_imports_data,
    patch_citizen_data,
)

cfg = TestConfig()


@pytest.mark.asyncio
async def test_patch_citizen(api_client):
    """
    Positive testcase: Test correctness of updating citizen info
    """

    # 2 import records are needed to check that patching one
    # import data doesn't affect another
    side_import_data = [
        generate_citizen(citizen_id=1),
        generate_citizen(citizen_id=2),
        generate_citizen(citizen_id=3),
    ]
    side_import_id = await post_imports_data(api_client, side_import_data)

    # Generate 3 citizens, where 2 of them are relatives
    import_data = [
        generate_citizen(
            citizen_id=1,
            name="Ivanov Ivan Ivanovich",
            gender="male",
            birth_date="01.01.2000",
            town="Some city/town",
            street="Some street",
            building="Some building",
            apartment=1,
            relatives=[2],
        ),
        generate_citizen(citizen_id=2, relatives=[1]),
        generate_citizen(citizen_id=3, relatives=[]),
    ]
    import_id = await post_imports_data(api_client, import_data)

    # data to modify and then patch it
    patch_data = import_data

    # Try to patch only one field
    patch_data[0]["name"] = "Ivanova Ionna Ivanovna"
    await patch_citizen_data(
        client=api_client,
        import_id=import_id,
        citizen_id=patch_data[0]["citizen_id"],
        data={"name": patch_data[0]["name"]},
    )

    # Patching all fields
    # Updating relations between citizens
    patch_data[0]["gender"] = "female"
    patch_data[0]["birth_date"] = "02.02.2002"
    patch_data[0]["town"] = "Another city/town"
    patch_data[0]["street"] = "Another street"
    patch_data[0]["building"] = "Another building"
    patch_data[0]["apartment"] += 5
    # Citizen with id 1 should lose relation with citizen
    # with id 2 and gain relation with citizen with id 3
    patch_data[0]["relatives"] = [patch_data[2]["citizen_id"]]

    patch_data[1]["relatives"].remove(patch_data[0]["citizen_id"])
    patch_data[2]["relatives"].append(patch_data[0]["citizen_id"])

    actual_data = await patch_citizen_data(
        client=api_client,
        import_id=import_id,
        citizen_id=patch_data[0]["citizen_id"],
        data={
            "gender": patch_data[0]["gender"],
            "birth_date": patch_data[0]["birth_date"],
            "town": patch_data[0]["town"],
            "street": patch_data[0]["street"],
            "building": patch_data[0]["building"],
            "apartment": patch_data[0]["apartment"],
            "relatives": patch_data[0]["relatives"],
        },
    )

    # Test correctness of the updating multiple fields of the citizen
    assert compare_citizens(actual_data, patch_data[0])

    # Test relations of all the citizens relations have been managed correctly
    actual_citizens = await get_citizens_data(api_client, import_id)
    assert compare_citizen_groups(actual_citizens, patch_data)

    # Test updating data of the second import record didn't make changes in
    # the first import record
    actual_citizens = await get_citizens_data(api_client, side_import_id)
    assert compare_citizen_groups(actual_citizens, side_import_data)


@pytest.mark.asyncio
async def test_patch_citizen_self_relative(api_client):
    """
    Positve testcase: Test a citizen can be updated to
    be a relative to themselves
    """

    # Generate 1 citizen
    import_data = [
        generate_citizen(
            citizen_id=1,
            name="Jake",
            gender="male",
            birth_date="14.06.1982",
            town="Dublin",
            relatives=[],
        ),
    ]
    import_id = await post_imports_data(api_client, import_data)

    # data to modify and then patch it
    patch_data = import_data

    patch_data[0]["relatives"] = [patch_data[0]["citizen_id"]]
    actual = await patch_citizen_data(
        client=api_client,
        import_id=import_id,
        citizen_id=patch_data[0]["citizen_id"],
        data={"relatives": patch_data[0]["relatives"]},
    )

    assert compare_citizens(actual, patch_data[0])


@pytest.mark.asyncio
async def test_patch_citizen_future_birthdate(api_client):
    """
    Negative testcase: Test a citizen can not be updated to
    have a birth date in the future
    """

    # Generate 1 citizen
    import_data = generate_citizens(citizens_number=1)
    import_id = await post_imports_data(api_client, import_data)

    # data to modify and then patch it
    patch_data = import_data

    new_birth_date = (date.today() + timedelta(days=3)).strftime(cfg.BIRTH_DATE_FORMAT)
    await patch_citizen_data(
        client=api_client,
        import_id=import_id,
        citizen_id=patch_data[0]["citizen_id"],
        data={"birth_date": new_birth_date},
        expected_status=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.asyncio
async def test_patch_citizen_nonexistent_relative(api_client):
    """
    Negative testcase: Test a citizen can not be updated to
    have a nonexistent in the import data relatives
    """

    # Generate 1 citizen
    import_data = [generate_citizen(citizen_id=1001)]
    import_id = await post_imports_data(api_client, import_data)

    # data to modify and then patch it
    patch_data = import_data

    await patch_citizen_data(
        client=api_client,
        import_id=import_id,
        citizen_id=patch_data[0]["citizen_id"],
        data={"relatives": [randint(1, 1000)]},
        expected_status=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.asyncio
async def test_patch_citizen_nonexistent_import_or_citizen(api_client):
    """
    Negative testcase: Test a nonexistent citizen can not be patched
    as well as a citizen in a nonexistent import record
    """

    # Test a citizen in a nonexistent import record can not be patched
    await patch_citizen_data(
        client=api_client,
        import_id=randint(1, 1000),
        citizen_id=randint(1, 1000),
        data={"name": "Ivan Ivanov"},
        expected_status=HTTPStatus.NOT_FOUND,
    )

    # Generate 1 citizen
    import_id = await post_imports_data(api_client, [])

    await patch_citizen_data(
        client=api_client,
        import_id=import_id,
        citizen_id=randint(1, 1000),
        data={"name": "Ivan Ivanov"},
        expected_status=HTTPStatus.NOT_FOUND,
    )
