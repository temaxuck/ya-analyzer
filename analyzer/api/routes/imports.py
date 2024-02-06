from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from aiomisc import chunk_list
from http import HTTPStatus
from marshmallow import ValidationError
from typing import Generator

from analyzer.api.schema import ImportSchema, ImportResponseSchema
from analyzer.db.schema import citizen_table, relation_table, import_table
from analyzer.utils.pg import MAX_QUERY_ARGS

from .base import BaseView


class ImportsView(BaseView):
    URL_PATH = "/imports"

    MAX_CITIZENS_PER_INSERT = MAX_QUERY_ARGS // len(citizen_table.columns)
    MAX_RELATIONS_PER_INSERT = MAX_QUERY_ARGS // len(relation_table.columns)

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
            yield (
                import_id,
                citizen["citizen_id"],
                citizen["name"],
                citizen["birth_date"],
                citizen["gender"],
                citizen["town"],
                citizen["street"],
                citizen["building"],
                citizen["apartment"],
            )

    @classmethod
    def make_relation_table_rows(cls, citizens, import_id) -> Generator:
        """
        Generate rows to insert into `relation_table` lazy.
        """

        for citizen in citizens:
            for relative_id in citizen["relatives"]:
                yield (import_id, citizen["citizen_id"], relative_id)

    @docs(summary="Add import with citizens info")
    @request_schema(ImportSchema())
    @response_schema(ImportResponseSchema(), code=HTTPStatus.CREATED.value)
    async def post(self):
        data = await self.request.json()
        async with self.pg.acquire() as conn:
            async with conn.cursor() as cur:
                async with cur.begin() as transaction:
                    try:
                        await cur.execute(
                            "INSERT INTO import DEFAULT VALUES RETURNING import_id"
                        )
                        import_id = await cur.fetchone()

                        citizens = data.get("citizens")
                        citizen_rows = self.make_citizen_table_rows(citizens, import_id)
                        relation_rows = self.make_relation_table_rows(
                            citizens, import_id
                        )

                        chunked_citizen_rows = chunk_list(
                            citizen_rows, self.MAX_CITIZENS_PER_INSERT
                        )
                        chunked_relation_rows = chunk_list(
                            relation_rows, self.MAX_RELATIONS_PER_INSERT
                        )

                        citizen_insert_query = """
                        INSERT INTO citizen (import_id, citizen_id, name, birth_date, gender, town, street, building, apartment)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """

                        relation_insert_query = """
                        INSERT INTO relation (import_id, citizen_id, relative_id)
                        VALUES (%s, %s, %s)
                        """

                        for chunk in chunked_citizen_rows:
                            for row in chunk:
                                await cur.execute(citizen_insert_query, row)

                        for chunk in chunked_relation_rows:
                            for row in chunk:
                                await cur.execute(relation_insert_query, row)

                    except Exception as e:
                        raise e
                        return web.json_response(
                            data={"error": str(e)}, status=HTTPStatus.BAD_REQUEST
                        )

        return web.json_response(
            data={"data": {"import_id": import_id}}, status=HTTPStatus.CREATED
        )
