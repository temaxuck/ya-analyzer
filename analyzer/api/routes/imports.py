from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from aiomisc import chunk_list
from datetime import datetime
from http import HTTPStatus
from typing import Generator
from sqlalchemy import insert

from analyzer.api.schema import ImportsSchema, ImportsResponseSchema
from analyzer.db.schema import citizen_table, relation_table, import_table
from analyzer.utils.pg import MAX_QUERY_ARGS

from .base import BaseView


class ImportsView(BaseView):
    URL_PATH = "/imports"

    MAX_CITIZENS_PER_INSERT = MAX_QUERY_ARGS // len(citizen_table.columns)
    MAX_RELATIONS_PER_INSERT = MAX_QUERY_ARGS // len(relation_table.columns)

    @classmethod
    def convert_client_date(cls, date):
        return datetime.strptime(date, "%d.%m.%Y").strftime("%Y-%m-%d")

    @classmethod
    def make_citizen_table_rows(cls, citizens, import_id) -> Generator:
        """
        Generate rows to insert into `citizen_table` lazy.

        Important:
            One generated row has no relatives field.
            Call `ImportsView.make_relations_table_rows(citizens, import_id)`
            to generate relatives for each citizen.
        """

        for citizen in citizens:
            yield {
                "import_id": import_id,
                "citizen_id": citizen["citizen_id"],
                "name": citizen["name"],
                "birth_date": cls.convert_client_date(citizen["birth_date"]),
                "gender": citizen["gender"],
                "town": citizen["town"],
                "street": citizen["street"],
                "building": citizen["building"],
                "apartment": citizen["apartment"],
            }

    @classmethod
    def make_relation_table_rows(cls, citizens, import_id) -> Generator:
        """
        Generate rows to insert into `relation_table` lazy.
        """

        for citizen in citizens:
            for relative_id in citizen["relatives"]:
                yield {
                    "import_id": import_id,
                    "citizen_id": citizen["citizen_id"],
                    "relative_id": relative_id,
                }

    @docs(summary="Add import with citizens info")
    @request_schema(ImportsSchema())
    @response_schema(ImportsResponseSchema(), code=HTTPStatus.CREATED.value)
    async def post(self):
        data = await self.request.json()
        async with self.pg.acquire() as conn:
            async with conn.begin() as transaction:
                try:
                    result = await conn.execute(
                        import_table.insert()
                        .values()
                        .returning(import_table.c.import_id)
                    )
                    import_id = await result.scalar()

                    citizens = data.get("citizens")
                    citizen_rows = self.make_citizen_table_rows(citizens, import_id)
                    relation_rows = self.make_relation_table_rows(citizens, import_id)

                    chunked_citizen_rows = chunk_list(
                        citizen_rows, self.MAX_CITIZENS_PER_INSERT
                    )
                    chunked_relation_rows = chunk_list(
                        relation_rows, self.MAX_RELATIONS_PER_INSERT
                    )

                    for chunk in chunked_citizen_rows:
                        await conn.execute(insert(citizen_table).values(chunk))

                    for chunk in chunked_relation_rows:
                        await conn.execute(insert(relation_table).values(chunk))

                except Exception as e:
                    raise e
                    return web.json_response(
                        data={"error": str(e)}, status=HTTPStatus.BAD_REQUEST
                    )

        return web.json_response(
            data={"data": {"import_id": import_id}}, status=HTTPStatus.CREATED
        )
