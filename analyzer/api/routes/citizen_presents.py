from aiohttp import web
from aiohttp_apispec import docs, response_schema
from itertools import groupby
from http import HTTPStatus
from sqlalchemy import Integer, cast, func, select, and_

from analyzer.api.schema import CitizenPresentsResponseSchema
from analyzer.db.schema import citizen_table, relation_table
from .base import BaseCitizenView


class CitizenPresentsView(BaseCitizenView):
    URL_PATH = r"/imports/{import_id:\d+}/citizens/presents"

    @docs(summary="Get data about how many presents do citizens buy each month")
    @response_schema(CitizenPresentsResponseSchema(), code=HTTPStatus.OK.value)
    async def get(self):
        await self.check_if_import_exists()

        month = func.date_part("month", citizen_table.c.birth_date)
        month = cast(month, Integer).label("month")

        query = (
            select(
                [
                    month,
                    relation_table.c.citizen_id,
                    func.count(relation_table.c.relative_id).label("presents"),
                ]
            )
            .select_from(
                relation_table.join(
                    citizen_table,
                    and_(
                        citizen_table.c.import_id == relation_table.c.import_id,
                        citizen_table.c.citizen_id == relation_table.c.relative_id,
                    ),
                )
            )
            .group_by(month, relation_table.c.import_id, relation_table.c.citizen_id)
            .where(relation_table.c.import_id == self.import_id)
        )

        async with self.pg.acquire() as conn:
            result = await conn.execute(query)
            rows = await result.fetchall()

        data = {i: [] for i in range(1, 13)}

        for month, rows in groupby(rows, key=lambda row: row["month"]):
            for row in rows:
                data[month].append(
                    {
                        "citizen_id": row["citizen_id"],
                        "presents": row["presents"],
                    }
                )

        return web.json_response(data={"data": data})
