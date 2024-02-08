from aiohttp import web
from aiohttp_apispec import docs, response_schema
from aiopg.sa.result import RowProxy
from datetime import date

from analyzer.utils.pg import SelectQuery
from analyzer.api.payload import AsyncGenJsonListPayload
from analyzer.api.schema import CitizensResponseSchema
from analyzer.db.schema import citizen_table, Gender
from .base import BaseCitizenView


class CitizensView(BaseCitizenView):
    URL_PATH = r"/imports/{import_id:\d+}/citizens"

    def serialize_row(self, row: RowProxy) -> dict:
        row = dict(row)

        for k, v in row.items():
            if isinstance(v, date):
                row[k] = v.strftime(self.app["config"].BIRTH_DATE_FORMAT)
            if isinstance(v, Gender):
                row[k] = v.value

        return row

    @docs(summary="Get citizens for the specified import")
    @response_schema(CitizensResponseSchema())
    async def get(self):
        await self.check_if_import_exists()

        query = self.CITIZENS_QUERY.where(citizen_table.c.import_id == self.import_id)

        async with self.pg.acquire() as conn:
            data = [self.serialize_row(row) async for row in SelectQuery(query, conn)]

        return web.json_response(data=data)
