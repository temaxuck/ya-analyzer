from aiohttp.typedefs import StrOrURL
from aiohttp.web_urldispatcher import DynamicResource
from aiohttp.test_utils import TestClient
from enum import EnumMeta
from faker import Faker
from http import HTTPStatus
from random import randint, choice, shuffle
from typing import Optional, List, Dict, Any, Mapping, Iterable, Union

from analyzer.api.routes import (
    ImportsView,
    CitizenView,
    CitizensView,
    CitizenPresentsView,
    AgeStatsView,
)
from analyzer.api.schema import (
    ImportsResponseSchema,
    CitizensResponseSchema,
    PatchCitizenResponseSchema,
    CitizenPresentsResponseSchema,
    AgeStatsResponseSchema,
)
from analyzer.config import TestConfig

CitizenType = Dict[str, Any]
MAX_INTEGER = 2147483647
cfg = TestConfig()

fake = Faker(["ru_RU", "en_US"])


def url_for(path: str, **kwargs) -> str:
    """
    Generate URL for dynamic aiohttp route with parameters
    """

    kwargs = {key: str(value) for key, value in kwargs.items()}

    return str(DynamicResource(path).url_for(**kwargs))


def generate_citizen(
    citizen_id: Optional[int] = None,
    name: Optional[str] = None,
    birth_date: Optional[str] = None,
    gender: Optional[str] = None,
    town: Optional[str] = None,
    street: Optional[str] = None,
    building: Optional[str] = None,
    apartment: Optional[int] = None,
    relatives: Optional[List[int]] = None,
) -> CitizenType:
    """
    Create and return a citizen data
    Auto fill not specified fields
    """

    if citizen_id is None:
        citizen_id = randint(0, MAX_INTEGER)

    if gender is None:
        gender = choice(("female", "male"))

    if name is None:
        name = fake.name_female() if gender == "female" else fake.name_male()

    if birth_date is None:
        birth_date = fake.date_of_birth(minimum_age=0, maximum_age=80).strftime(
            cfg.BIRTH_DATE_FORMAT
        )

    if town is None:
        town = fake.city_name()

    if street is None:
        street = fake.street_name()

    if building is None:
        building = str(randint(1, 100))

    if apartment is None:
        apartment = randint(1, 120)

    if relatives is None:
        relatives = []

    return {
        "citizen_id": citizen_id,
        "name": name,
        "birth_date": birth_date,
        "gender": gender,
        "town": town,
        "street": street,
        "building": building,
        "apartment": apartment,
        "relatives": relatives,
    }


def generate_citizens(
    citizens_number: int,
    relations_number: Optional[int] = None,
    unique_towns: int = 20,
    start_citizen_id: int = 0,
    **citizen_kwargs,
) -> List[CitizenType]:
    """
    Generate list of citizens data

    :param citizens_num: Number of citizens
    :param relations_num: Number of relations one citizen should have
    :param unique_towns: Number of unique cities within one import
    :param start_citizen_id: `citizen_id` to start incrementing from
    :param citizen_kwargs: Arguments generate_citizen
    """

    towns = [fake.city_name() for _ in range(unique_towns)]
    citizens = {}

    max_citizen_id = start_citizen_id + citizens_number
    for citizen_id in range(start_citizen_id, max_citizen_id):
        citizen_kwargs["town"] = citizen_kwargs.get("town", choice(towns))
        citizens[citizen_id] = generate_citizen(citizen_id=citizen_id, **citizen_kwargs)

    unassigned_relatives = relations_number or citizens_number // 10
    shuffled_citizen_ids = list(citizens.keys())

    while unassigned_relatives:
        shuffle(shuffled_citizen_ids)

        citizen_id = shuffled_citizen_ids[0]

        for relative_id in shuffled_citizen_ids[1:]:
            if relative_id not in citizens[citizen_id]["relatives"]:
                citizens[citizen_id]["relatives"].append(relative_id)
                citizens[relative_id]["relatives"].append(citizen_id)
                break
        else:
            raise ValueError("Unable to choose relative for citizen")

        unassigned_relatives -= 1

    return list(citizens.values())


def normalize_citizen(citizen: Mapping) -> Mapping:
    """
    Make citizen comparable with other citizens
    """
    return {**citizen, "relatives": sorted(citizen["relatives"])}


def compare_citizens(left: Mapping, right: Mapping) -> bool:
    return normalize_citizen(left) == normalize_citizen(right)


def compare_citizen_groups(left: Iterable, right: Iterable) -> bool:
    left = [normalize_citizen(citizen) for citizen in left]
    left.sort(key=lambda citizen: citizen["citizen_id"])

    right = [normalize_citizen(citizen) for citizen in right]
    right.sort(key=lambda citizen: citizen["citizen_id"])

    return left == right


async def post_imports_data(
    client: TestClient,
    citizens: List[Mapping[str, Any]],
    expected_status: Union[int, EnumMeta] = HTTPStatus.CREATED,
    **request_kwargs,
) -> Optional[int]:
    response = await client.post(
        ImportsView.URL_PATH,
        json={"citizens": citizens},
        **request_kwargs,
    )

    assert response.status == expected_status

    if response.status == HTTPStatus.CREATED:
        data = await response.json()
        errors = ImportsResponseSchema().validate(data)
        assert errors == {}
        return data["data"]["import_id"]


async def get_citizens_data(
    client: TestClient,
    import_id: int,
    expected_status: Union[int, EnumMeta] = HTTPStatus.OK,
    **request_kwargs,
) -> List[CitizenType]:
    response = await client.get(
        url_for(CitizensView.URL_PATH, import_id=import_id),
        **request_kwargs,
    )

    assert response.status == expected_status

    if response.status == HTTPStatus.OK:
        data = await response.json()
        errors = CitizensResponseSchema().validate(data)
        assert errors == {}
        return data["data"]


async def patch_citizen_data(
    client: TestClient,
    import_id: int,
    citizen_id: int,
    data: CitizenType,
    expected_status: Union[int, EnumMeta] = HTTPStatus.OK,
    str_or_url: StrOrURL = CitizenView.URL_PATH,
    **request_kwargs,
) -> CitizenType:
    response = await client.patch(
        url_for(str_or_url, import_id=import_id, citizen_id=citizen_id),
        json={"data": data},
        **request_kwargs,
    )

    assert response.status == expected_status

    if response.status == HTTPStatus.OK:
        data = await response.json()
        errors = PatchCitizenResponseSchema().validate(data)
        assert errors == {}
        return data["data"]


async def get_citizen_presents_data(
    client: TestClient,
    import_id: int,
    expected_status: Union[int, EnumMeta] = HTTPStatus.OK,
    **request_kwargs,
) -> CitizenType:
    response = await client.get(
        url_for(CitizenPresentsView.URL_PATH, import_id=import_id),
        **request_kwargs,
    )

    assert response.status == expected_status

    if response.status == HTTPStatus.OK:
        data = await response.json()
        errors = CitizenPresentsResponseSchema().validate(data)
        assert errors == {}
        return data["data"]


async def get_age_stats_data(
    client: TestClient,
    import_id: int,
    expected_status: Union[int, EnumMeta] = HTTPStatus.OK,
    **request_kwargs,
) -> CitizenType:
    response = await client.get(
        url_for(AgeStatsView.URL_PATH, import_id=import_id),
        **request_kwargs,
    )

    assert response.status == expected_status

    if response.status == HTTPStatus.OK:
        data = await response.json()
        errors = AgeStatsResponseSchema().validate(data)
        assert errors == {}
        return data["data"]
