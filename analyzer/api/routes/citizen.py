import logging


from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp_apispec import docs, request_schema, response_schema
from aiopg.sa import SAConnection
from datetime import date, datetime
from aiopg.sa.result import RowProxy
from marshmallow import ValidationError
from sqlalchemy import and_, or_
from typing import List

from analyzer.api.schema import PatchCitizenSchema, PatchCitizenResponseSchema
from analyzer.db.schema import citizen_table, relation_table
from .base import BaseCitizenView


logger = logging.getLogger(__name__)


class CitizenView(BaseCitizenView):
    URL_PATH = r"/imports/{import_id:\d+}/citizens/{citizen_id:\d+}"

    @property
    def citizen_id(self):
        return int(self.request.match_info.get("citizen_id"))

    @classmethod
    def convert_client_date(cls, date: date) -> datetime:
        return datetime.strptime(date, "%d.%m.%Y").strftime("%Y-%m-%d")

    async def acquire_lock(self, conn: SAConnection, import_id: int) -> None:
        await conn.execute("SELECT pg_advisory_xact_lock(%s)", (import_id,))

    async def get_citizen(
        self,
        conn: SAConnection,
        import_id: int,
        citizen_id: int,
    ) -> RowProxy:
        query = self.CITIZENS_QUERY.where(
            and_(
                citizen_table.c.import_id == import_id,
                citizen_table.c.citizen_id == citizen_id,
            )
        )

        result = await conn.execute(query)

        return await result.fetchone()

    async def update_citizen(
        self,
        conn: SAConnection,
        import_id: int,
        citizen: RowProxy,
        data: dict,
    ) -> None:
        values = {k: v for k, v in data.items() if k != "relatives"}

        if "birth_date" in values:
            values["birth_date"] = self.convert_client_date(values["birth_date"])

        if values:
            query = (
                citizen_table.update()
                .values(values)
                .where(
                    and_(
                        citizen_table.c.import_id == import_id,
                        citizen_table.c.citizen_id == citizen.get("citizen_id"),
                    )
                )
            )
            await conn.execute(query)

        if "relatives" in data:
            cur_relatives = set(citizen.get("relatives", []))
            new_relatives = set(data.get("relatives"))
            await self.remove_relatives(
                conn,
                self.import_id,
                citizen.get("citizen_id"),
                cur_relatives - new_relatives,
            )

            await self.add_relatives(
                conn,
                self.import_id,
                citizen.get("citizen_id"),
                new_relatives - cur_relatives,
            )

    async def add_relatives(
        self,
        conn: SAConnection,
        import_id: int,
        citizen_id: int,
        relative_ids: List[int],
    ) -> None:
        if not relative_ids:
            return

        values = []
        base = {"import_id": import_id}

        for relative_id in relative_ids:
            values.append(
                {
                    **base,
                    "citizen_id": citizen_id,
                    "relative_id": relative_id,
                }
            )

            if citizen_id != relative_id:
                values.append(
                    {
                        **base,
                        "citizen_id": relative_id,
                        "relative_id": citizen_id,
                    }
                )

        query = relation_table.insert().values(values)

        try:
            await conn.execute(query)
        except Exception as err:
            logger.error(str(err))
            raise ValidationError(
                {
                    "relatives": (
                        f"Unable to add relatives {relative_ids}, some do not exist"
                    )
                }
            )

    async def remove_relatives(
        self,
        conn: SAConnection,
        import_id: int,
        citizen_id: int,
        relative_ids: List[int],
    ) -> None:
        if not relative_ids:
            return

        conditions = []
        for relative_id in relative_ids:
            conditions.extend(
                [
                    and_(
                        relation_table.c.import_id == import_id,
                        relation_table.c.citizen_id == citizen_id,
                        relation_table.c.relative_id == relative_id,
                    ),
                    and_(
                        relation_table.c.import_id == import_id,
                        relation_table.c.citizen_id == relative_id,
                        relation_table.c.relative_id == citizen_id,
                    ),
                ]
            )

        query = relation_table.delete().where(or_(*conditions))
        await conn.execute(query)

    @docs(summary="Update citizen data from import `import_id` with id `citizen_id`")
    @request_schema(PatchCitizenSchema())
    @response_schema(PatchCitizenResponseSchema())
    async def patch(self):
        data = await self.request.json()
        async with self.pg.acquire() as conn:
            async with conn.begin() as _:

                # set advisory lock for the transaction isolation
                # so another transaction would wait until this transaction proceeds
                await self.acquire_lock(conn, self.import_id)

                citizen = await self.get_citizen(conn, self.import_id, self.citizen_id)

                if not citizen:
                    raise HTTPNotFound()

                await self.update_citizen(
                    conn,
                    self.import_id,
                    citizen,
                    data["data"],
                )

                citizen = await self.get_citizen(conn, self.import_id, self.citizen_id)

        return web.json_response(data={"data": self.serialize_row(citizen)})
