from aiohttp import web
from aiohttp_apispec import docs, response_schema

from analyzer.utils.pg import SelectQuery
from analyzer.api.schema import CitizensResponseSchema
from analyzer.db.schema import citizen_table
from .base import BaseCitizenView


class CitizensView(BaseCitizenView):
    URL_PATH = r"/imports/{import_id:\d+}/citizens"

    @docs(summary="Get citizens for the specified import")
    @response_schema(CitizensResponseSchema())
    async def get(self):
        await self.check_if_import_exists()

        query = self.CITIZENS_QUERY.where(citizen_table.c.import_id == self.import_id)

        async with self.pg.acquire() as conn:
            data = [self.serialize_row(row) async for row in SelectQuery(query, conn)]

        return web.json_response(data={"data": data})
