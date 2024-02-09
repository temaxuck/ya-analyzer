from aiohttp import web
from aiohttp_apispec import docs, response_schema
from sqlalchemy import func, select, text

from analyzer.api.schema import AgeStatsResponseSchema
from analyzer.db.schema import citizen_table
from analyzer.utils.pg import rounded
from .base import BaseCitizenView


class AgeStatsView(BaseCitizenView):
    URL_PATH = r"/imports/{import_id:\d+}/cities/stats/percentile/age"
    CURRENT_DATE = text("TIMEZONE('utc', CURRENT_TIMESTAMP)")

    @docs(summary="Citizens age stats grouped by city")
    @response_schema(AgeStatsResponseSchema())
    async def get(self):
        await self.check_if_import_exists()

        age = func.age(self.CURRENT_DATE, citizen_table.c.birth_date)
        age = func.date_part("year", age)

        query = (
            select(
                [
                    citizen_table.c.town,
                    rounded(func.percentile_cont(0.5).within_group(age)).label("p50"),
                    rounded(func.percentile_cont(0.75).within_group(age)).label("p75"),
                    rounded(func.percentile_cont(0.99).within_group(age)).label("p99"),
                ]
            )
            .select_from(citizen_table)
            .group_by(citizen_table.c.town)
            .where(citizen_table.c.import_id == self.import_id)
        )

        async with self.pg.acquire() as conn:
            result = await conn.execute(query)
            stats = [self.serialize_row(row) for row in await result.fetchall()]

        return web.json_response(data={"data": stats})
