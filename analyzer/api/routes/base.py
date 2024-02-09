"""
    Resource `View` base classes
"""

from aiohttp import web
from aiopg.sa.result import RowProxy
from datetime import date
from sqlalchemy.sql import Select
from sqlalchemy import select, func, and_

from analyzer.db.schema import citizen_table, relation_table, import_table, Gender


class BaseView(web.View):
    URL_PATH: str

    @property
    def app(self) -> web.Application:
        return self.request.app

    @property
    def pg(self) -> "Pool":
        return self.request.app["pg"]


class BaseImportView(BaseView):
    @property
    def import_id(self) -> int:
        return int(self.request.match_info.get("import_id"))

    async def check_if_import_exists(self) -> None:
        async with self.pg.acquire() as conn:
            result = await conn.execute(
                import_table.select().where(import_table.c.import_id == self.import_id)
            )
            import_id = await result.scalar()

            if not import_id:
                raise web.HTTPNotFound()


class BaseCitizenView(BaseImportView):

    def serialize_row(self, row: RowProxy) -> dict:
        row = dict(row)

        for k, v in row.items():
            if isinstance(v, date):
                row[k] = v.strftime(self.app["config"].BIRTH_DATE_FORMAT)
            if isinstance(v, Gender):
                row[k] = v.value

        return row

    @property
    def CITIZENS_QUERY(self) -> Select:
        return (
            select(
                [
                    citizen_table.c.citizen_id,
                    citizen_table.c.name,
                    citizen_table.c.birth_date,
                    citizen_table.c.gender,
                    citizen_table.c.town,
                    citizen_table.c.street,
                    citizen_table.c.building,
                    citizen_table.c.apartment,
                    func.array_remove(
                        func.array_agg(relation_table.c.relative_id), None
                    ).label("relatives"),
                ]
            )
            .select_from(
                citizen_table.outerjoin(
                    relation_table,
                    and_(
                        citizen_table.c.import_id == relation_table.c.import_id,
                        citizen_table.c.citizen_id == relation_table.c.citizen_id,
                    ),
                )
            )
            .group_by(
                citizen_table.c.import_id,
                citizen_table.c.citizen_id,
            )
        )
